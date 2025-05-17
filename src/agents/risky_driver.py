import random
import traci
from .base_agent import BaseAgent
from src.simulation.tls_recorder import TLSEventRecorder

class RiskyDriver(BaseAgent):
    """
    A driver that takes an aggressive but situationally aware approach to traffic lights:
    • Accelerates on amber when far from the stop line
    • Gambles on close ambers with a configurable probability
    • Rolls a fresh red only if within a small dilemma zone
    """

    def __init__(self, vehicle_id: str, route: str, recorder: TLSEventRecorder):
        super().__init__(vehicle_id, route)
        # Comfortable deceleration (m/s²)
        self.a_c = 4.5
        # Maximum acceleration (m/s²)
        self.a_max = 2.6
        # Buffer to delay braking relative to safe stopping distance (m)
        self.risky_buffer = 2.0
        # Dilemma zone for red-roll (m)
        self.red_run_zone = 1.5
        # Probability of “go” on close amber
        self.amber_go_prob = 0.7
        # Track last TLS state for fresh-red detection
        self.last_tls_state = None
        # Duration to apply acceleration (s)
        self.accel_duration = 1.0
        # TLS event recorder
        self.recorder = recorder

    def update(self):
        # Query upcoming traffic light
        next_tls = traci.vehicle.getNextTLS(self.vehicle_id)
        if not next_tls:
            desired_speed = traci.vehicle.getMaxSpeed(self.vehicle_id)
            traci.vehicle.setSpeed(self.vehicle_id, desired_speed)
            return

        # Unpack TraCI response
        tls_id, tls_index, dist, _ = next_tls[0]
        raw_state = traci.trafficlight.getRedYellowGreenState(tls_id)
        st = raw_state.lower()  # e.g. 'grgr', 'yryr'

        # Record new encounters
        if 'y' in st and (self.last_tls_state is None or 'y' not in self.last_tls_state):
            self.recorder.saw_amber()
        if 'r' in st and (self.last_tls_state is None or 'r' not in self.last_tls_state):
            self.recorder.saw_red()

        v = traci.vehicle.getSpeed(self.vehicle_id)
        d = dist
        desired_speed = traci.vehicle.getMaxSpeed(self.vehicle_id)
        d_stop = (v**2) / (2 * self.a_c) if self.a_c > 0 else float('inf')
        d_risky = max(0.0, d_stop - self.risky_buffer)

        print(f"[RiskyDriver] {self.vehicle_id}: TLS={tls_id}, raw_state={raw_state}, d={d:.2f}, v={v:.2f}, d_stop={d_stop:.2f}, d_risky={d_risky:.2f}")

        # ────── GREEN ──────
        if 'g' in st:
            traci.vehicle.setSpeed(self.vehicle_id, desired_speed)

        # ────── AMBER ──────
        elif 'y' in st:
            if d > d_risky:
                traci.vehicle.setAcceleration(self.vehicle_id, self.a_max, self.accel_duration)
                # going on amber far → run event
                self.recorder.ran_amber()
            else:
                if random.random() < self.amber_go_prob:
                    traci.vehicle.setSpeed(self.vehicle_id, desired_speed)
                    # gamble go on close amber → run
                    self.recorder.ran_amber()
                else:
                    traci.vehicle.setDecel(self.vehicle_id, self.a_c)

        # ────── RED ──────
        elif 'r' in st:
            just_switched = (self.last_tls_state == 'y')
            if just_switched and d <= self.red_run_zone:
                traci.vehicle.setSpeed(self.vehicle_id, desired_speed)
                # fresh red roll → run
                self.recorder.ran_red()
            else:
                traci.vehicle.setDecel(self.vehicle_id, self.a_c)

        # Store state for next comparison
        self.last_tls_state = st
