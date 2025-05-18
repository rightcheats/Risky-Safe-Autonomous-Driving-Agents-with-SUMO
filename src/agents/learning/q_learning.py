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

def compute_reward(prev_state, action, new_state):
    if prev_state[0] == 'red' and action == 'go':
        return -1
    if prev_state[0] == 'green' and action == 'go':
        return +1
    return 0
