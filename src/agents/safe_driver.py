import logging

import traci
from src.simulation.tls_recorder import TLSEventRecorder
from .learning.q_learning_driver import QLearningDriver
from .learning.rewards import safe_reward

logger = logging.getLogger(__name__)


class SafeDriver(QLearningDriver):
    """
    A driver that stops on red, slows on amber, then clears the intersection,
    with discrete state encoding for tabular Q-learning.
    """

    DECEL_AMBER = 2.6  # m/s²
    DECEL_RED = 4.5    # m/s²
    STOP_MARGIN = 0.5  # m buffer to ensure full stop before line

    def __init__(self, vehicle_id: str, recorder: TLSEventRecorder):
        super().__init__(
            vehicle_id=vehicle_id,
            recorder=recorder,
            actions=['STOP', 'SLOW', 'GO'],
            alpha=0.1,
            gamma=0.9,
            epsilon=1.0,
        )
        # Internal FSM state for rule-based fall-backs / logging
        self.state = 'approach'

    def encode_state(self) -> tuple[str, int, int]:
        """
        Encode the current TLS phase, distance bin, and speed bin into a hashable tuple.
        Returns:
            (phase, dist_bin, speed_bin)
        """
        next_tls = traci.vehicle.getNextTLS(self.vehicle_id)
        if not next_tls:
            # Free road → treat as GREEN, farthest distance, current speed bin
            speed = traci.vehicle.getSpeed(self.vehicle_id)
            return 'GREEN', 3, self._speed_bin(speed)

        tls_id, _, dist, _ = next_tls[0]
        raw = traci.trafficlight.getRedYellowGreenState(tls_id)
        if 'g' in raw:
            phase = 'GREEN'
        elif 'y' in raw:
            phase = 'AMBER'
        else:
            phase = 'RED'

        # Distance bins: [0–10)=0, [10–20)=1, [20–40)=2, [40+)=3
        if dist <= 10:
            dist_b = 0
        elif dist <= 20:
            dist_b = 1
        elif dist <= 40:
            dist_b = 2
        else:
            dist_b = 3

        speed = traci.vehicle.getSpeed(self.vehicle_id)
        speed_b = self._speed_bin(speed)

        return phase, dist_b, speed_b

    def _speed_bin(self, speed: float) -> int:
        """
        0 = stopped, 1 = slow (<=5 m/s), 2 = cruise (>5 m/s)
        """
        if speed == 0:
            return 0
        return 1 if speed <= 5 else 2

    def compute_reward(
        self,
        prev_state: tuple[str, int, int],
        action: str,
        new_state: tuple[str, int, int],
    ) -> float:
        """
        Delegate to the shared safe_reward function for tabular Q-learning.
        """
        r = safe_reward(prev_state, action, new_state)
        logger.debug(
            "SafeDriver %s: %s --%s--> %s = reward %.3f",
            self.vehicle_id, prev_state, action, new_state, r,
        )
        return r

    def apply_action(self, action: str) -> None:
        """
        Map the abstract action into TraCI calls.
        """
        if action == 'STOP':
            traci.vehicle.setSpeed(self.vehicle_id, 0.0)
            logger.debug("%s applied STOP", self.vehicle_id)

        elif action == 'SLOW':
            traci.vehicle.slowDown(
                self.vehicle_id, 0.0, SafeDriver.DECEL_AMBER
            )
            logger.debug(
                "%s applied SLOW (decel=%.1f)", 
                self.vehicle_id, SafeDriver.DECEL_AMBER
            )

        elif action == 'GO':
            desired = traci.vehicle.getMaxSpeed(self.vehicle_id)
            traci.vehicle.setSpeed(self.vehicle_id, desired)
            logger.debug("%s applied GO (speed=%.2f)", self.vehicle_id, desired)
