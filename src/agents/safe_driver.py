import traci
from src.simulation.tls_recorder import TLSEventRecorder

class SafeDriver:
    """
    A driver that stops on red, slows on amber, then clears the intersection,
    with added stopping-distance checks and debug logging.
    """
    DECEL_AMBER = 2.6  # m/s²
    DECEL_RED = 4.5    # m/s²
    STOP_MARGIN = 0.5  # m buffer to ensure full stop before line

    def __init__(self, vid: str, recorder: TLSEventRecorder):
        self.vid = vid
        self.recorder = recorder
        self.state = 'approach'  # approach, slowing, stopped, passing

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

        # Debug logging
        speed = traci.vehicle.getSpeed(self.vid)
        # print(f"[SafeDriver] {self.vid}: phase={phase}, dist={dist:.2f}, speed={speed:.2f}, state={self.state}")

        # Handle amber transition
        if 'y' in phase and self.state == 'approach':
            self.recorder.saw_amber()
            self.state = 'slowing'
            traci.vehicle.slowDown(self.vid, 0.0, SafeDriver.DECEL_AMBER)
            print(f"[SafeDriver] {self.vid} saw amber → slowing (DECEL_AMBER={SafeDriver.DECEL_AMBER})")

        # Handle red transition with stopping-distance guard
        elif 'r' in phase and self.state in ('approach', 'slowing'):
            self.recorder.saw_red()
            self.state = 'stopped'
            # compute stopping distance
            v = traci.vehicle.getSpeed(self.vid)
            d_stop = (v ** 2) / (2 * SafeDriver.DECEL_RED) if SafeDriver.DECEL_RED > 0 else float('inf')
            if dist > d_stop + SafeDriver.STOP_MARGIN:
                traci.vehicle.slowDown(self.vid, 0.0, SafeDriver.DECEL_RED)
                print(f"[SafeDriver] {self.vid} decelerating for red (d_stop={d_stop:.2f})")
            else:
                # emergency stop to avoid crossing line
                traci.vehicle.setSpeed(self.vid, 0.0)
                print(f"[SafeDriver] {self.vid} emergency stop (dist={dist:.2f} <= d_stop+margin) ")

        # Once stopped on red, wait for green to go
        if self.state == 'stopped' and 'g' in phase:
            self.state = 'passing'
            desired = traci.vehicle.getMaxSpeed(self.vid)
            traci.vehicle.setSpeed(self.vid, desired)
            print(f"[SafeDriver] {self.vid} green after red → passing at speed={desired}")

        # If slowed on amber, clear when green
        if self.state == 'slowing' and 'g' in phase:
            self.state = 'passing'
            desired = traci.vehicle.getMaxSpeed(self.vid)
            traci.vehicle.setSpeed(self.vid, desired)
            print(f"[SafeDriver] {self.vid} green after amber → passing at speed={desired}")

        # After passing the TLS, return to approach state
        if self.state == 'passing' and dist < -2.0:
            self.state = 'approach'
            print(f"[SafeDriver] {self.vid} passed intersection → approach state reset")
