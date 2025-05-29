import logging
import random
import traci
from src.simulation.tls_recorder import TLSEventRecorder
from .learning.q_learning_driver import QLearningDriver
from .learning.rewards import risky_reward

logger = logging.getLogger(__name__)

N_TTL_BINS = 4

class RiskyDriver(QLearningDriver):
    """
    Risky driving style 
        - prioritises speed,
        - runs ambers and some reds,
        - disregards some traffic laws e.g. speeds
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
            actions=[
                'STOP', 'SLOW',
                'GO_COMPLIANT', 'GO_OVERSHOOT_S', 'GO_OVERSHOOT_L',
            ],
            alpha=0.1,
            gamma=0.9,
            epsilon=1.0,
        )

        self.route = route
        self.last_tls_phase: str | None = None

        # motion parameters
        self.a_c = 4.5
        self.a_max = 2.6
        self.accel_duration = 1.0 
        
        self.max_speed_excess: float = 2.0 # allowed to explore double the speed limit
        self.small_excess_ratio: float = 1.2 # small overshoot

    def encode_state(self) -> tuple[str,int,int,int]:
        """
        Returns (phase, dist_bin, speed_bin, ttl_bin)
        Logs first-seen amber/red to recorder
        """
        next_tls = traci.vehicle.getNextTLS(self.vehicle_id)
        if not next_tls:
            speed = traci.vehicle.getSpeed(self.vehicle_id)
            return 'GREEN', 3, self._speed_bin(speed), N_TTL_BINS-1

        tls_id, _, dist, _ = next_tls[0]

        raw   = traci.trafficlight.getRedYellowGreenState(tls_id).lower()
        phase = 'GREEN' if 'g' in raw else ('AMBER' if 'y' in raw else 'RED')
        self.last_tls_phase = phase

        # distance bins
        if dist <= 10: dist_b = 0
        elif dist <= 20: dist_b = 1
        elif dist <= 40: dist_b = 2
        else: dist_b = 3

        speed = traci.vehicle.getSpeed(self.vehicle_id)
        speed_b = self._speed_bin(speed)
        ttl_b   = self._time_to_red_bin(tls_id)

        return phase, dist_b, speed_b, ttl_b

    def _speed_bin(self, v: float) -> int:
        """
        0: stopped
        1: at or below limit
        2: small overshoot (<= small_excess_ratio * limit)
        3: large overshoot (> small_excess_ratio up to max)
        """
        if v == 0:
            return 0
        allowed = traci.vehicle.getAllowedSpeed(self.vehicle_id)  # ← new
        if v <= allowed:
            return 1
        elif v <= allowed * self.small_excess_ratio:
            return 2
        else:
            return 3

    # mimic human drivers who make informed guesses on time of light state
    def _time_to_red_bin(self, tls_id: str) -> int:

        switch_time = traci.trafficlight.getNextSwitch(tls_id)
        now = traci.simulation.getTime()
        total_dur = traci.trafficlight.getPhaseDuration(tls_id)
        ttl_frac = max(0.0, (switch_time - now) / total_dur)
        return min(N_TTL_BINS-1, int(ttl_frac * N_TTL_BINS))

    def compute_reward(
        self,
        prev_state: tuple[str,int,int,int],
        action: str,
        new_state: tuple[str,int,int,int],
        decel: float
    ) -> float:
        
        # extract dist_bin from prev state
        dist_bin = prev_state[1]
        max_dist_bin = 3
        r = risky_reward(prev_state, action, new_state, dist_bin, max_dist_bin)

        phase = prev_state[0]
        if phase == "AMBER" and action == "GO":
            self.recorder.ran_amber()
        if phase == "RED" and action == "GO":
            self.recorder.ran_red()
        if phase == "GREEN" and action == "GO":
            self.recorder.ran_green()

        # reward/penalise based on overshoot for speed
        _, _, speed_b, _ = new_state
        if speed_b == 2:
            r += 0.2     # small bonus for slight speeding
        elif speed_b == 3:
            r -= 0.5     # penalty for too much

        # logger.debug(
        #     "RiskyDriver %s: %s --%s--> %s = %.3f",
        #     self.vehicle_id, prev_state, action, new_state, r
        # )

        return r

    def apply_action(self, action: str) -> None:
        allowed = traci.vehicle.getAllowedSpeed(self.vehicle_id)
        if action == 'STOP':
            traci.vehicle.setSpeed(self.vehicle_id, 0.0)
        elif action == 'SLOW':
            traci.vehicle.slowDown(self.vehicle_id, 0.0, self.a_c)
        elif action == 'GO_COMPLIANT':
            traci.vehicle.setSpeed(self.vehicle_id, allowed)
        elif action == 'GO_OVERSHOOT_S':
            traci.vehicle.setSpeed(self.vehicle_id, allowed * self.small_excess_ratio)
        elif action == 'GO_OVERSHOOT_L':
            traci.vehicle.setSpeed(self.vehicle_id, allowed * self.max_speed_excess)
        else:
            logger.error("RiskyDriver %s: unknown action %r", self.vehicle_id, action)