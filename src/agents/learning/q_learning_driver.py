import traci
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
        self.prev_speed = None

    @abstractmethod
    def encode_state(self):
        """Encode current simulator state into a hashable tuple"""
        ...

    @abstractmethod
    def compute_reward(self, prev_state, action, new_state, decel):
        """Return scalar reward for given transition"""
        ...

    @abstractmethod
    def apply_action(self, action):
        """Execute chosen action in simulator"""
        ...

    def update(self):
        """
        Compute decel = max(prev_speed - curr_speed, 0)
        Call compute_reward(prev_state, last_action, state, decel)
        Q-table update
        Choose & apply next action
        """
        state = self.encode_state()
        curr_speed = traci.vehicle.getSpeed(self.vehicle_id)

        # q-update
        if self.prev_state is not None:
            decel = max(0.0, (self.prev_speed or 0.0) - curr_speed)
            r = self.compute_reward(self.prev_state, self.last_action, state, decel)
            self.qtable.update(self.prev_state, self.last_action, r, state)

        # select n execute action
        action = self.qtable.choose_action(state)
        self.apply_action(action)

        # store for next step
        self.prev_state  = state
        self.last_action = action
        self.prev_speed  = curr_speed
