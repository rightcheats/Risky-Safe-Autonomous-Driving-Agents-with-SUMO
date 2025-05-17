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
                'amber_encountered': 0,
                'prev_speed': None,
                'collision_count': 0,  # NEW: collision counter
            }

        # Simulation loop
        for step in range(self.max_steps):
            traci.simulationStep()
            agent_manager.update_agents(step)

            # fetch vehicles involved in collisions this step
            colliding_vehicles = traci.simulation.getCollidingVehiclesIDList()

            for vid, rec in data.items():
                if vid not in traci.vehicle.getIDList():
                    continue

                # increment collision count if in collision list
                if vid in colliding_vehicles:
                    rec['collision_count'] += 1

                # Distance & edges
                rec['edges_visited'].add(traci.vehicle.getRoadID(vid))
                rec['total_distance'] = traci.vehicle.getDistance(vid)

                # Traffic lights encountered
                tls_list = traci.vehicle.getNextTLS(vid)
                for tls_data in tls_list:
                    tls_id, state, dist, *extra = tls_data
                    if dist <= 10.0:
                        rec['tls_encountered'].add(tls_id)
                        if 'y' in str(state).lower():
                            rec['amber_encountered'] += 1

                # Wait time accumulation & stops
                speed = traci.vehicle.getSpeed(vid)
                prev = rec['prev_speed']
                if prev is not None and prev > 0 and speed == 0:
                    rec['tls_stop_count'] += 1
                if speed == 0:
                    rec['tls_wait_time'] += self.step_length
                rec['prev_speed'] = speed

                # Check destination
                if not rec['reached'] and traci.vehicle.getRoadID(vid) == dest:
                    rec['reached'] = True
                    rec['end_step'] = step

            if all(r['reached'] for r in data.values()):
                break

        traci.close()
        return data, route_idx
