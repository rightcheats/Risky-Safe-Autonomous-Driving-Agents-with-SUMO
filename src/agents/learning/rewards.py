# extra reward for accelerating in green, extra penalty for slowing/brking
R_GREEN = 0.5  
K_DECEL  = 0.1  

def safe_reward(prev_state, action, new_state, decel: float) -> float:
    """
    Reward for SafeDriver:
        - stop on red
        - cautious on amber (slows), shouldn't run
        - go on green
    """
    phase = prev_state[0]
    reward = 0.0

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
        reward += 0.5
    # penalise small overshoot
    elif action == 'GO_OVERSHOOT_S':
        reward -= 0.5
    # heavily penalise large overshoot
    elif action == 'GO_OVERSHOOT_L':
        reward -= 1.0

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

    # --- TLS
    # reward any go on green
    if phase == 'GREEN' and is_go:
         reward += R_GREEN * (dist_bin / max_dist_bin) # give higher reward if green further 
    # reward any go on amber
    if phase == 'AMBER' and is_go:
         reward += 0.3
    # penalise stop on green
    if phase == 'GREEN' and action == 'STOP':
        reward -= 1.0
    # penalise any go on red
    if phase == 'RED' and is_go:
         reward -= 0.9

    # --- SPEED COMPLIANCE
    # extra bonus for compliant go on green
    if action == 'GO_COMPLIANT' and phase == 'GREEN':
        reward += 0.2

    # overshoots
    if action == 'GO_OVERSHOOT_S':
        reward += 0.4   # small speeding bonus
    elif action == 'GO_OVERSHOOT_L':
        reward += 20   # large speeding penalty

    return reward
