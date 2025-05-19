from abc import ABC, abstractmethod
from src.agents.learning.q_table import QTable
import logging

logger = logging.getLogger(__name__)

class QLearningDriver(ABC):
    def __init__(self, vehicle_id, recorder, actions, alpha, gamma, epsilon):
        self.vehicle_id = vehicle_id
        self.recorder = recorder
        self.qtable = QTable(actions, alpha, gamma, epsilon)
        self.prev_state = None
        self.last_action = None

    @abstractmethod
    def encode_state(self):
        """Encode the current simulator state into a hashable tuple."""
        ...

    @abstractmethod
    def compute_reward(self, prev_state, action, new_state):
        """Return the scalar reward for the given transition."""
        ...

    @abstractmethod
    def apply_action(self, action):
        """Execute the chosen action in the simulator."""
        ...

    def update(self):
        """Perform one Q-learning step: update Q, select & apply next action."""
        state = self.encode_state()

        # 1) Q-table update
        if self.prev_state is not None:
            r = self.compute_reward(self.prev_state, self.last_action, state)
            self.qtable.update(self.prev_state, self.last_action, r, state)

        # 2) Choose & execute next action
        action = self.qtable.choose_action(state)
        self.apply_action(action)

        # 3) Store for next iteration
        self.prev_state, self.last_action = state, action
