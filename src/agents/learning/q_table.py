from collections import defaultdict
import random
import logging
import os
import pickle

logger = logging.getLogger(__name__)

class QTable:
    """Tabular Q-learning: maintains q-values, chooses actions,
    applies updates, & handles epsilon-decay"""

    def __init__(
        self,
        actions: list[str],
        alpha: float = 0.1,
        gamma: float = 0.9,
        epsilon: float = 1.0,
    ):
        self.actions = actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon

        # q maps state -> q value for action
        self.Q: dict = defaultdict(lambda: [0.0 for _ in actions])

    def __repr__(self) -> str:
        return (
            f"QTable(actions={self.actions}, alpha={self.alpha}, "
            f"gamma={self.gamma}, epsilon={self.epsilon}, "
            f"entries={len(self.Q)})"
        )

    def choose_action(self, state):
        """Epsilon-greedy selection: random with prob epsilon or best-known action"""
        if random.random() < self.epsilon or state not in self.Q:
            action = random.choice(self.actions)
            #logger.debug("Exploring: chose %s in state %s", action, state)
            return action

        q_vals = self.Q[state]
        max_q = max(q_vals)
        best_actions = [
            act for act, q in zip(self.actions, q_vals) if q == max_q
        ]
        action = random.choice(best_actions)
        # logger.debug("Exploiting: chose %s in state %s", action, state)
        return action

    def update(self, state, action, reward, next_state):
        """Perform the Q-learning update for a single transition"""
        action_idx = self.actions.index(action)
        old_value = self.Q[state][action_idx]
        future_estimate = max(self.Q[next_state])
        td_target = reward + self.gamma * future_estimate
        td_error = td_target - old_value
        self.Q[state][action_idx] += self.alpha * td_error

        # logger.debug(
        #     "Q[%s][%s] updated: old=%.3f → new=%.3f",
        #     state,
        #     action,
        #     old_value,
        #     self.Q[state][action_idx],
        # )

    def decay_epsilon(self, decay_rate: float, min_epsilon: float = 0.01):
        """Anneal epsilon after each episode/step-to-step decay"""
        old_eps = self.epsilon
        self.epsilon = max(min_epsilon, self.epsilon * decay_rate)
        # logger.info("Epsilon decayed: %.4f → %.4f", old_eps, self.epsilon)

    def save(self, filepath: str) -> None:
        """Persist Q-table"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump({
                "Q": dict(self.Q),
                "epsilon": self.epsilon
            }, f)

    def load(self, filepath: str) -> None:
        """Load Q-table if exists"""
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                data = pickle.load(f)
            # rewrap into defaultdict
            self.Q = defaultdict(lambda: [0.0]*len(self.actions), data["Q"])
            # gets overwritten
            self.epsilon = data.get("epsilon", self.epsilon)