import traci
from src.simulation.tls_recorder import TLSEventRecorder

class SafeDriver:
    """
    A driver that stops on red, slows on amber, then clears the intersection.
    """
    DECEL_AMBER = 2.6  # m/s²
    DECEL_RED = 4.5    # m/s²

    def __init__(self, vid: str, recorder: TLSEventRecorder):
        self.vid = vid
        self.recorder = recorder
        self.state = 'approach'  # approach, slowing, stopped, passing

    def update(self):
        next_tls = traci.vehicle.getNextTLS(self.vid)
        if not next_tls:
            return

        # Correct unpack: (tlsID, tlsIndex, distance, state)
        tls_id, tls_index, dist, raw_state = next_tls[0]
        phase = raw_state.lower()  # e.g. 'grgr', 'yryr'

        # on entering amber or red, record encounter
        if 'y' in phase and self.state == 'approach':
            self.recorder.saw_amber()
            self.state = 'slowing'
            traci.vehicle.slowDown(self.vid, 0.0, SafeDriver.DECEL_AMBER)
        elif 'r' in phase and self.state in ('approach', 'slowing'):
            self.recorder.saw_red()
            self.state = 'stopped'
            traci.vehicle.slowDown(self.vid, 0.0, SafeDriver.DECEL_RED)

        # once stopped on red, wait until green
        if self.state == 'stopped' and 'g' in phase:
            self.recorder.ran_red()
            self.state = 'passing'
            traci.vehicle.setSpeed(self.vid, traci.vehicle.getMaxSpeed(self.vid))

        # once slowed on amber, if light turns green before full stop
        if self.state == 'slowing' and 'g' in phase:
            self.recorder.ran_amber()
            self.state = 'passing'
            traci.vehicle.setSpeed(self.vid, traci.vehicle.getMaxSpeed(self.vid))

        # clear intersection, then go back to approach
        if self.state == 'passing' and dist < -2.0:
            self.state = 'approach'
