# extra reward for accelerating in green, extra penalty for slowing/brking
R_GREEN = 0.5  
K_DECEL  = 0.08  

def safe_reward(prev_state, action, new_state, decel: float, epsilon: float) -> float:
    """
    Reward for SafeDriver:
        - stop on red
        - cautious on amber (slows), shouldn't run
        - go on green
    """
    phase = prev_state[0]
    # small baseline to diversify early actions by encouraging go
    is_go = action.startswith('GO')
    reward = 0.1 if is_go else 0.0

    # --- TLS
    # penalises any go on red
    is_go = action.startswith('GO')
    if phase == 'RED' and is_go:
        return -1.0
    # rewards any go on green
    if phase == 'GREEN' and is_go:
        reward += 1.0
    # penalise  stop on green
    if phase == 'GREEN' and action == 'STOP':
        reward -= 0.5
    # reward slow on amber
    if phase == 'AMBER' and action == 'SLOW':
        reward += 0.5
    # penalise any go on amber
    if phase == 'AMBER' and is_go:
        reward -= 0.5

    # --- BRAKING
    # scaled brake penalty
    if action in ('STOP', 'SLOW'):
        reward -= K_DECEL * decel

    # SPEED COMPLIANCE
    # reward going the speed limit
    if action == 'GO_COMPLIANT':
        reward += 0.2
    elif action == 'GO_OVERSHOOT_S':
        # early on (ε≈1) you get +0.5; later (ε→0) you get –0.5
        reward += epsilon * 0.5 + (1 - epsilon) * (-0.5)
    elif action == 'GO_OVERSHOOT_L':
        # early on +0.3; later –1.0
        reward += epsilon * 0.3 + (1 - epsilon) * (-1.0)

    return reward

def risky_reward(prev_state, action, new_state, dist_bin: int, max_dist_bin: int) -> float:
    """
    Reward for RiskyDriver:
        - always gets small reward for going
        - should run greens and ambers
        - shouldnt always run red, but some is fine
    """
    phase = prev_state[0]
    
    # treat any GO_* as GO
    is_go = action.startswith('GO')
    # baseline small  reward for going 
    reward = 0.2 if is_go else -0.1

    # --- TLS incentives
    if phase == 'GREEN' and is_go:
        reward += R_GREEN * (dist_bin / max_dist_bin)
    if phase == 'AMBER' and is_go:
        reward += 0.3
    if phase == 'GREEN' and action == 'STOP':
        reward -= 1.0
    if phase == 'RED' and is_go:
        reward -= 0.9

    # --- SPEED STRATEGY
    ttl_bin = new_state[3]  # stage of learning

    if action == 'GO_COMPLIANT' and phase in ['GREEN', 'AMBER']:
        reward += 1.0
    if action == 'GO_OVERSHOOT_S':
        reward += 3.0
    elif action == 'GO_OVERSHOOT_L':
        reward += 3.0 * ttl_bin

    return reward
