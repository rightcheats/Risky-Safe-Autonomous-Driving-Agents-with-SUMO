# simulation_runner.py

import traci

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
        # Start SUMO and inject agents
        traci.start(self.cmd)
        agent_manager.inject_agents()
        dest = agent_manager.get_destination_edge()
        route_idx = agent_manager.get_route_label()

        # Initialize per-agent record
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
                'amber_encountered': 0,     # proximity count
                'red_encountered': 0,       # proximity count
                'amber_run_count': 0,       # actual run-throughs on amber
                'red_run_count': 0,         # actual run-throughs on red
                'tls_last_state': {},       # TLS ID → last-seen color
                'max_speed': 0.0,           # record peak instantaneous speed
                'prev_speed': None,
                'collision_count': 0,
            }

        # Simulation loop
        for step in range(self.max_steps):
            traci.simulationStep()
            agent_manager.update_agents(step)

            # vehicles involved in collisions this step
            colliding = traci.simulation.getCollidingVehiclesIDList()

            for vid, rec in data.items():
                if vid not in traci.vehicle.getIDList():
                    continue

                # collision counting
                if vid in colliding:
                    rec['collision_count'] += 1

                # update distance & edges visited
                rec['edges_visited'].add(traci.vehicle.getRoadID(vid))
                rec['total_distance'] = traci.vehicle.getDistance(vid)

                # record next-TLS info
                next_tls = traci.vehicle.getNextTLS(vid)
                seen_ids = set()
                for tls_id, state, dist, *extra in next_tls:
                    seen_ids.add(tls_id)
                    state_str = str(state).lower()
                    rec['tls_last_state'][tls_id] = state_str

                    # proximity counts
                    if dist <= 10.0:
                        rec['tls_encountered'].add(tls_id)
                        if 'y' in state_str:
                            rec['amber_encountered'] += 1
                        elif 'r' in state_str:
                            rec['red_encountered'] += 1

                # detect actual run-throughs (TLS dropped out of next_tls)
                passed = set(rec['tls_last_state'].keys()) - seen_ids
                for tls_id in passed:
                    last_state = rec['tls_last_state'].pop(tls_id)
                    if 'y' in last_state:
                        rec['amber_run_count'] += 1
                    elif 'r' in last_state:
                        rec['red_run_count'] += 1

                # current speed & max-speed update
                speed = traci.vehicle.getSpeed(vid)
                if speed > rec['max_speed']:
                    rec['max_speed'] = speed

                # stops & wait time at TLS
                prev = rec['prev_speed']
                if prev is not None and prev > 0 and speed == 0:
                    rec['tls_stop_count'] += 1
                if speed == 0:
                    rec['tls_wait_time'] += self.step_length
                rec['prev_speed'] = speed

                # check if reached destination
                if not rec['reached'] and traci.vehicle.getRoadID(vid) == dest:
                    rec['reached'] = True
                    rec['end_step'] = step

            if all(r['reached'] for r in data.values()):
                break

        traci.close()
        return data, route_idx
