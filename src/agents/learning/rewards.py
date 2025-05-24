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

    if phase == 'RED' and action == 'GO':
        return -1.0
    if phase == 'GREEN' and action == 'GO':
        reward += +1.0
    if phase == 'GREEN' and action == 'STOP':
        reward -= 0.5
    if phase == 'AMBER' and action == 'SLOW':
        reward += 0.5
    if phase == 'AMBER' and action == 'GO':
        reward -= 0.5

    # scaled brake penalty - prev had harsher breaking than risky (?)
    if action in ('STOP', 'SLOW'):
        reward -= K_DECEL * decel

    return reward

def risky_reward(prev_state, action, new_state, dist_bin: int, max_dist_bin: int) -> float:
    """
    Reward for RiskyDriver:
        - always gets small reward for going
        - should run greens and ambers
        - shouldnt always run red, but some is fine
    """
    phase = prev_state[0]
    
    reward = +0.2 if action == 'GO' else -0.1

    if phase == 'GREEN' and action == 'GO':
        reward += R_GREEN * (dist_bin / max_dist_bin)
    if phase == 'AMBER' and action == 'GO':
        reward += +0.3
    if phase == 'GREEN' and action == 'STOP':
        reward -= 1.0
    # TODO: should this be this harsh?
    if phase == 'RED' and action == 'GO':
        reward -= 1.0

    return reward
