import logging
import traci

from src.simulation.tls_recorder import TLSEventRecorder
from .learning.q_learning_driver import QLearningDriver
from .learning.rewards import safe_reward

# debug config
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ignore noisy libs
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# how many bins for time-to-red
N_TTL_BINS = 4

class SafeDriver(QLearningDriver):
    """
    Safe/cautious driving style, prioritises safety, stops on amber
    """
    
    DECEL_AMBER = 2.6  
    DECEL_RED   = 4.5  
    STOP_MARGIN = 0.5  
    SPEED_PENALTY = 1.0

    def __init__(self, vehicle_id: str, recorder: TLSEventRecorder):
        super().__init__(
            vehicle_id=vehicle_id,
            recorder=recorder,
            actions=['STOP', 'SLOW', 'GO'],
            alpha=0.1,
            gamma=0.9,
            epsilon=1.0,
        )
        self.state = 'approach'

        self.last_tls_phase: str | None = None

    def encode_state(self) -> tuple[str,int,int,int]:
        """
        Returns (phase, dist_bin, speed_bin, ttl_bin)
        """

        next_tls = traci.vehicle.getNextTLS(self.vehicle_id)

        if not next_tls:
            # free road = treat like green/farthest tls
            speed = traci.vehicle.getSpeed(self.vehicle_id)
            return 'GREEN', 3, self._speed_bin(speed), N_TTL_BINS-1

        tls_id, _, dist, _ = next_tls[0]

        #NOTE: logic now done in simulation_runner.py isntead
        # raw   = traci.trafficlight.getRedYellowGreenState(tls_id).lower()

        # phase = 'GREEN' if 'g' in raw else ('AMBER' if 'y' in raw else 'RED')

        # if self.last_tls_phase is None or phase != self.last_tls_phase:
        #     if phase == 'AMBER':
        #         self.recorder.saw_amber()
        #     elif phase == 'RED':
        #         self.recorder.saw_red()

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
        ttl_b = self._time_to_red_bin(tls_id)

        return phase, dist_b, speed_b, ttl_b

    #NOTE: new = add q learning for speed
    def _speed_bin(self, speed: float) -> int:
        if speed == 0:
            return 0
        # compare against lane's allowed speed
        allowed = traci.vehicle.getAllowedSpeed(self.vehicle_id)
        speed_b = 1 if speed <= allowed else 2
        logger.debug(
            "SafeDriver %s: speed=%.2f, allowed=%.2f → speed_bin=%d",
            self.vehicle_id, speed, allowed, speed_b
        )
        return speed_b

    def _time_to_red_bin(self, tls_id: str) -> int:
        """
        Represent time until next switch into discrete value
        """
        # TODO: check tuple size unpack
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
        
        r = safe_reward(prev_state, action, new_state, decel)

        # penalty for > speed limit
        _, _, speed_b, _ = new_state
        if speed_b == 2:
            r -= SafeDriver.SPEED_PENALTY
            logger.debug(
                "SafeDriver %s: overspeed detected (bin=2), applying penalty=%.2f",
                self.vehicle_id, SafeDriver.SPEED_PENALTY
            )

        #NOTE: check this works
        phase = prev_state[0]
        if phase == "AMBER" and action == "GO":
            self.recorder.ran_amber()
        if phase == "RED" and action == "GO":
            self.recorder.ran_red()
        if phase == "GREEN" and action == "GO":
            self.recorder.ran_green()

        # logger.debug(
        #     "SafeDriver %s: %s --%s--> %s | decel=%.2f = %.3f",
        #     self.vehicle_id, prev_state, action, new_state, decel, r
        # )

        return r

    def apply_action(self, action: str) -> None:
        if action == 'STOP':
            traci.vehicle.setSpeed(self.vehicle_id, 0.0)
        elif action == 'SLOW':
            traci.vehicle.slowDown(
                self.vehicle_id, 0.0, SafeDriver.DECEL_AMBER
            )
        else:  # GO action = comply with current speed limit
            allowed = traci.vehicle.getAllowedSpeed(self.vehicle_id)
            traci.vehicle.setSpeed(self.vehicle_id, allowed)
            logger.debug(
                "SafeDriver %s applied GO → setSpeed=%.2f (allowed)",
                self.vehicle_id, allowed
            )
