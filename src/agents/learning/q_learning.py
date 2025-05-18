import random
from collections import defaultdict

class QTable:
    def __init__(self, actions, alpha=0.1, gamma=0.9, epsilon=1.0):
        self.actions = actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        # Q is a dict: state → [Q for each action]
        self.Q = defaultdict(lambda: [0.0 for _ in actions])

    def __repr__(self):
        return (
            f"QTable(actions={self.actions}, "
            f"alpha={self.alpha}, gamma={self.gamma}, "
            f"epsilon={self.epsilon}, entries={len(self.Q)})"
        )
    
    def choose_action(self, state):
        if random.random() < self.epsilon or state not in self.Q:
            return random.choice(self.actions)
        q_vals = self.Q[state]
        max_q = max(q_vals)
        best = [a for a, q in zip(self.actions, q_vals) if q == max_q]
        return random.choice(best)

#TODO: this is only for safedriver so rename this file/function
def compute_reward(prev_state, action, new_state):
    """
    Returns a scalar reward for a transition (prev_state, action) → new_state.
    """
    phase = prev_state[0]

    # heavy penalty for running a red
    if phase == 'RED' and action == 'GO':
        return -1.0
    # reward correct go on green
    if phase == 'GREEN' and action == 'GO':
        return +1.0
    # penalty for unnecessarily stopping on green
    if phase == 'GREEN' and action == 'STOP':
        return -0.5
    # encourage cautious slow on amber
    if phase == 'AMBER' and action == 'SLOW':
        return +0.5
    # discourage running through amber
    if phase == 'AMBER' and action == 'GO':
        return -0.5

    return 0.0

