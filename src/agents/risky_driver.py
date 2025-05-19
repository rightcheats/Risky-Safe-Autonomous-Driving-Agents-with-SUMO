import logging
import traci

from src.simulation.tls_recorder import TLSEventRecorder
from .learning.q_learning_driver import QLearningDriver
from .learning.rewards import risky_reward

logger = logging.getLogger(__name__)

class RiskyDriver(QLearningDriver):
    """
    A driver that takes an aggressive but situationally aware approach to traffic lights:
    • Accelerates on amber when far from the stop line
    • Gambles on close ambers with a configurable probability
    • Rolls a fresh red only if within a small dilemma zone
    """

    def __init__(
        self,
        vehicle_id: str,
        route: str,
        recorder: TLSEventRecorder
    ):
        super().__init__(
            vehicle_id=vehicle_id,
            recorder=recorder,
            actions=['STOP', 'SLOW', 'GO'],
            alpha=0.1,
            gamma=0.9,
            epsilon=1.0,
        )
        # Preserve route if needed elsewhere
        self.route = route

        # Risky‐driver parameters
        self.a_c = 4.5            # comfortable deceleration (m/s²)
        self.a_max = 2.6          # maximum acceleration (m/s²)
        self.risky_buffer = 2.0   # buffer for braking distance (m)
        self.red_run_zone = 1.5   # fresh-red run zone (m)
        self.amber_go_prob = 0.7  # P(go) on close amber
        self.accel_duration = 1.0 # duration for setAcceleration calls (s)

        # For TLS-event recording in encode_state
        self.last_tls_state: str | None = None

    def encode_state(self) -> tuple[str, int, int]:
        """
        Encode the current TLS phase, distance bin, and speed bin.
        Also records 'saw_amber' / 'saw_red' events when the light first changes.
        """
        next_tls = traci.vehicle.getNextTLS(self.vehicle_id)
        if not next_tls:
            # Free road → GREEN, farthest distance bin, current speed bin
            speed = traci.vehicle.getSpeed(self.vehicle_id)
            return 'GREEN', 3, self._speed_bin(speed)

        tls_id, _, dist, _ = next_tls[0]
        raw = traci.trafficlight.getRedYellowGreenState(tls_id).lower()

        # Record initial amber/red sightings
        if self.last_tls_state is None or raw != self.last_tls_state:
            if 'y' in raw and (self.last_tls_state is None or 'y' not in self.last_tls_state):
                self.recorder.saw_amber()
            if 'r' in raw and (self.last_tls_state is None or 'r' not in self.last_tls_state):
                self.recorder.saw_red()
        self.last_tls_state = raw

        # Map raw string → phase
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
        """0=stopped, 1=slow (<=5 m/s), 2=cruise (>5 m/s)."""
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
        Compute scalar reward and record any 'ran_amber' or 'ran_red' events
        when the agent chooses GO on amber/red.
        """
        reward = risky_reward(prev_state, action, new_state)

        phase = prev_state[0]
        if phase == 'AMBER' and action == 'GO':
            self.recorder.ran_amber()
        if phase == 'RED' and action == 'GO':
            self.recorder.ran_red()

        logger.debug(
            "RiskyDriver %s: %s --%s--> %s = reward %.3f",
            self.vehicle_id, prev_state, action, new_state, reward,
        )
        return reward

    def apply_action(self, action: str) -> None:
        """
        Execute the chosen action in SUMO via TraCI.
        """
        if action == 'STOP':
            traci.vehicle.setSpeed(self.vehicle_id, 0.0)
            logger.debug("%s applied STOP", self.vehicle_id)

        elif action == 'SLOW':
            traci.vehicle.setDecel(self.vehicle_id, self.a_c)
            logger.debug(
                "%s applied SLOW (decel=%.2f)", 
                self.vehicle_id, self.a_c
            )

        elif action == 'GO':
            max_speed = traci.vehicle.getMaxSpeed(self.vehicle_id)
            traci.vehicle.setSpeed(self.vehicle_id, max_speed)
            logger.debug("%s applied GO (speed=%.2f)", self.vehicle_id, max_speed)