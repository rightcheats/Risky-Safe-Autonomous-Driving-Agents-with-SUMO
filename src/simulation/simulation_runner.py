# simulation_runner.py

import traci

# threshold in m/s² above which we call it sudden braking
SUDDEN_BRAKE_THRESHOLD = 3.0

class SimulationRunner:
    """
    Starts a SUMO simulation, injects agents, steps through
    and collects raw per-agent data (journey + TLS metrics).
    """
    def __init__(self, sumo_binary: str, sumo_config: str,
                 max_steps: int = 3000, step_length: float = 1.0):
        self.cmd = [
            sumo_binary, "-c", sumo_config,
            "--start", "--no-warnings", "--no-step-log", "--quit-on-end"
        ]
        self.max_steps = max_steps
        self.step_length = step_length

    def run(self, agent_manager):
        traci.start(self.cmd)
        agent_manager.inject_agents()
        dest = agent_manager.get_destination_edge()
        route_idx = agent_manager.get_route_label()

        data = {}
        for vid in ["safe_1", "risky_1"]:
            data[vid] = {
                'reached': False,
                'end_step': None,
                'total_distance': 0.0,
                'edges_visited': set(),
                'tls_encountered': set(),
                'tls_stop_count': 0,
                'tls_wait_time': 0.0,
                'amber_encountered': 0,
                'red_encountered': 0,
                'amber_run_count': 0,
                'red_run_count': 0,
                'tls_last_state': {},
                'max_speed': 0.0,
                'sudden_brake_count': 0,    # count of high-decel events
                'max_decel': 0.0,           # peak deceleration seen
                'sum_decel': 0.0,           # sum of decelerations on those events
                'prev_speed': None,
                'collision_count': 0,
            }

        for step in range(self.max_steps):
            traci.simulationStep()
            agent_manager.update_agents(step)
            colliding = traci.simulation.getCollidingVehiclesIDList()

            for vid, rec in data.items():
                if vid not in traci.vehicle.getIDList():
                    continue

                # collisions
                if vid in colliding:
                    rec['collision_count'] += 1

                # distance & edges
                rec['edges_visited'].add(traci.vehicle.getRoadID(vid))
                rec['total_distance'] = traci.vehicle.getDistance(vid)

                # TLS proximity & run-through logic...
                next_tls = traci.vehicle.getNextTLS(vid)
                seen_ids = set()
                for tls_id, state, dist, *extra in next_tls:
                    seen_ids.add(tls_id)
                    st = str(state).lower()
                    rec['tls_last_state'][tls_id] = st
                    if dist <= 10.0:
                        rec['tls_encountered'].add(tls_id)
                        if 'y' in st:
                            rec['amber_encountered'] += 1
                        elif 'r' in st:
                            rec['red_encountered'] += 1

                passed = set(rec['tls_last_state']) - seen_ids
                for tls_id in passed:
                    last = rec['tls_last_state'].pop(tls_id)
                    if 'y' in last:
                        rec['amber_run_count'] += 1
                    elif 'r' in last:
                        rec['red_run_count'] += 1

                # speed, max-speed
                speed = traci.vehicle.getSpeed(vid)
                if speed > rec['max_speed']:
                    rec['max_speed'] = speed

                # sudden braking (deceleration)
                prev = rec['prev_speed']
                if prev is not None:
                    delta_v = prev - speed
                    decel = delta_v / self.step_length
                    if decel > SUDDEN_BRAKE_THRESHOLD:
                        rec['sudden_brake_count'] += 1
                        rec['sum_decel'] += decel
                        if decel > rec['max_decel']:
                            rec['max_decel'] = decel

                # TLS stops & wait time
                if prev is not None and prev > 0 and speed == 0:
                    rec['tls_stop_count'] += 1
                if speed == 0:
                    rec['tls_wait_time'] += self.step_length

                rec['prev_speed'] = speed

                # reached destination?
                if not rec['reached'] and traci.vehicle.getRoadID(vid) == dest:
                    rec['reached'] = True
                    rec['end_step'] = step

            if all(r['reached'] for r in data.values()):
                break

        traci.close()
        return data, route_idx
