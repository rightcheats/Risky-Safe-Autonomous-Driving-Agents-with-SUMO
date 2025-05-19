from collections import defaultdict

def safe_reward(
    prev_state: tuple[str, ...],
    action: str,
    new_state: tuple[str, ...],
) -> float:
    """Reward function for the SafeDriver agent.

    Args:
        prev_state: Encoded as (phase, ...).
        action: One of 'STOP', 'SLOW', 'GO'.
        new_state: New encoded state after action.

    Returns:
        A scalar reward encouraging safe TLS behavior.
    """
    phase = prev_state[0]

    if phase == 'RED' and action == 'GO':
        return -1.0
    if phase == 'GREEN' and action == 'GO':
        return +1.0
    if phase == 'GREEN' and action == 'STOP':
        return -0.5
    if phase == 'AMBER' and action == 'SLOW':
        return +0.5
    if phase == 'AMBER' and action == 'GO':
        return -0.5

    return 0.0


def risky_reward(
    prev_state: tuple[str, ...],
    action: str,
    new_state: tuple[str, ...],
) -> float:
    """Reward function for the RiskyDriver agent.

    Args:
        prev_state: Encoded as (phase, ...).
        action: One of 'STOP', 'SLOW', 'GO'.
        new_state: New encoded state after action.

    Returns:
        A scalar reward that encourages speed but penalizes unsafe red-runs.
    """
    phase = prev_state[0]
    # base: small positive for GO, small negative otherwise
    reward = +0.2 if action == 'GO' else -0.1

    # bonus for running amber
    if phase == 'AMBER' and action == 'GO':
        reward += +0.3

    # mild penalty for stopping on green (slows you down unnecessarily)
    if phase == 'GREEN' and action == 'STOP':
        reward -= 0.2

    # penalty for red-run
    if phase == 'RED' and action == 'GO':
        reward -= 1.0

    return reward
