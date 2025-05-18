import traci
from src.simulation.tls_recorder import TLSEventRecorder
from .learning.q_learning import QTable, compute_reward

class SafeDriver:
    """
    A driver that stops on red, slows on amber, then clears the intersection,
    with added stopping-distance checks and discrete state encoding for Q-learning.
    """
    DECEL_AMBER = 2.6  # m/s²
    DECEL_RED = 4.5    # m/s²
    STOP_MARGIN = 0.5  # m buffer to ensure full stop before line

    def __init__(self, vid: str, recorder: TLSEventRecorder):
        self.vid = vid
        self.recorder = recorder

        # Q‐learning setup
        self.qtable = QTable(
            actions=['STOP','SLOW','GO'],
            alpha=0.1,      # learning rate
            gamma=0.9,      # discount factor
            epsilon=1.0     # start fully exploratory
        )
        self.prev_state = None
        self.last_action = None

        self.state = 'approach'  # approach, slowing, stopped, passing

    def get_state(self):
        """
        Map to 3-phase states, 4 distance bins, and 3 speed bins.
        """
        next_tls = traci.vehicle.getNextTLS(self.vid)
        if not next_tls:
            # Free road: treat as GREEN-equivalent, farthest distance bin, current speed bin
            speed = traci.vehicle.getSpeed(self.vid)
            return ('GREEN', 3, self._speed_bin(speed))

        tls_id, _, dist, _ = next_tls[0]
        # Determine phase via the red‐yellow‐green string
        tls_state = traci.trafficlight.getRedYellowGreenState(tls_id)
        if 'g' in tls_state:
            phase = 'GREEN'
        elif 'y' in tls_state:
            phase = 'AMBER'
        else:
            phase = 'RED'

        # Distance bins: 0–10→0, 10–20→1, 20–40→2, >40→3
        if dist <= 10:
            dist_b = 0
        elif dist <= 20:
            dist_b = 1
        elif dist <= 40:
            dist_b = 2
        else:
            dist_b = 3

        speed = traci.vehicle.getSpeed(self.vid)
        speed_b = self._speed_bin(speed)

        return (phase, dist_b, speed_b)

    def _speed_bin(self, speed: float) -> int:
        """
        0 = stopped (0 m/s)
        1 = slow (0 < speed <= 5 m/s)
        2 = cruise (speed > 5 m/s)
        """
        if speed == 0:
            return 0
        elif speed <= 5:
            return 1
        else:
            return 2

    def update(self):
        # Query upcoming traffic light
        next_tls = traci.vehicle.getNextTLS(self.vid)
        if not next_tls:
            # No TLS ahead: cruise at max speed
            desired = traci.vehicle.getMaxSpeed(self.vid)
            traci.vehicle.setSpeed(self.vid, desired)
            return

        tls_id, tls_index, dist, raw_state = next_tls[0]
        phase = raw_state.lower()  # e.g. 'grgr', 'yryr'

        # Existing rule-based logic…
        speed = traci.vehicle.getSpeed(self.vid)

        if 'y' in phase and self.state == 'approach':
            self.recorder.saw_amber()
            self.state = 'slowing'
            traci.vehicle.slowDown(self.vid, 0.0, SafeDriver.DECEL_AMBER)
            print(f"[SafeDriver] {self.vid} saw amber → slowing (DECEL_AMBER={SafeDriver.DECEL_AMBER})")

        elif 'r' in phase and self.state in ('approach', 'slowing'):
            self.recorder.saw_red()
            self.state = 'stopped'
            v = traci.vehicle.getSpeed(self.vid)
            d_stop = (v ** 2) / (2 * SafeDriver.DECEL_RED) if SafeDriver.DECEL_RED > 0 else float('inf')
            if dist > d_stop + SafeDriver.STOP_MARGIN:
                traci.vehicle.slowDown(self.vid, 0.0, SafeDriver.DECEL_RED)
                print(f"[SafeDriver] {self.vid} decelerating for red (d_stop={d_stop:.2f})")
            else:
                traci.vehicle.setSpeed(self.vid, 0.0)
                print(f"[SafeDriver] {self.vid} emergency stop (dist={dist:.2f} <= d_stop+margin) ")

        if self.state == 'stopped' and 'g' in phase:
            self.state = 'passing'
            desired = traci.vehicle.getMaxSpeed(self.vid)
            traci.vehicle.setSpeed(self.vid, desired)
            print(f"[SafeDriver] {self.vid} green after red → passing at speed={desired}")

        if self.state == 'slowing' and 'g' in phase:
            self.state = 'passing'
            desired = traci.vehicle.getMaxSpeed(self.vid)
            traci.vehicle.setSpeed(self.vid, desired)
            print(f"[SafeDriver] {self.vid} green after amber → passing at speed={desired}")

        if self.state == 'passing' and dist < -2.0:
            self.state = 'approach'
            print(f"[SafeDriver] {self.vid} passed intersection → approach state reset")

        #  Q-learning update & action selection 
        state = self.get_state()
        print(f"DEBUG STATE: {state}")

        # if we have a previous step, update Q(prev_state, last_action)
        if self.prev_state is not None:
            reward = compute_reward(self.prev_state, self.last_action, state)
            i = self.qtable.actions.index(self.last_action)
            old_q = self.qtable.Q[self.prev_state][i]
            future_q = max(self.qtable.Q[state])
            # q-learning formula
            self.qtable.Q[self.prev_state][i] += self.qtable.alpha * (
                reward + self.qtable.gamma * future_q - old_q
            )
            print(f"DEBUG Q{self.prev_state}[{self.last_action}] = {self.qtable.Q[self.prev_state][i]:.3f} (r={reward})")

        # choose next action
        action = self.qtable.choose_action(state)
        print(f"DEBUG ACTION: {action}")

        # choose action safedriver executes
        if action == 'STOP':
            traci.vehicle.setSpeed(self.vid, 0.0)
        elif action == 'SLOW':
            traci.vehicle.slowDown(self.vid, 0.0, SafeDriver.DECEL_AMBER)
        elif action == 'GO':
            desired = traci.vehicle.getMaxSpeed(self.vid)
            traci.vehicle.setSpeed(self.vid, desired)

        # store for next step
        self.prev_state = state
        self.last_action = action

