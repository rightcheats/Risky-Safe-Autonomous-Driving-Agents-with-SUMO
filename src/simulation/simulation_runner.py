import traci

SUDDEN_BRAKE_THRESHOLD = 3.0

class SimulationRunner:
    """
    - starts SUMO simulation
    - injects agents, 
    - collects raw per-agent data
    """
    def __init__(self, sumo_binary: str, sumo_config: str,
                 max_steps: int = 3000, step_length: float = 1.0):
        mem = max_steps * step_length
        self.cmd = [
            sumo_binary, "-c", sumo_config,
            "--start", "--no-warnings", "--no-step-log",
            f"--waiting-time-memory", str(mem),
            "--quit-on-end"
        ]
        self.max_steps = max_steps
        self.step_length = step_length

    def run(self, agent_manager):
        data = {}
        route_idx = None

        try:
            traci.start(self.cmd)
            agent_manager.inject_agents()
            dest = agent_manager.get_destination_edge()
            route_idx = agent_manager.get_route_label()

            # init agent records
            for vid in ["safe_1", "risky_1"]:
                data[vid] = {
                    'reached': False,
                    'end_step': None,
                    'total_distance': 0.0,
                    'edges_visited': set(),
                    'tls_encountered': set(),
                    'tls_stop_count': 0,
                    'amber_encountered': 0,
                    'red_encountered': 0,
                    'amber_run_count': 0,
                    'red_run_count': 0,
                    'tls_last_state': {},
                    'max_speed': 0.0,
                    'sudden_brake_count': 0,
                    'max_decel': 0.0,
                    'sum_decel': 0.0,
                    'lane_change_count': 0,
                    'prev_speed': None,
                    'prev_lane': None,
                    'collision_count': 0,
                    'wait_time': 0.0,
                }

            # simulation loop
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

                    # TLS stuff
                    next_tls = traci.vehicle.getNextTLS(vid)
                    seen_ids = set()
                    for tls_id, state, dist_raw, *extra in next_tls:
                        dist = float(dist_raw)
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
                        if last == 'y':
                            rec['tls_stop_count'] += 1

                    # speed stuff
                    # max speed
                    speed = traci.vehicle.getSpeed(vid)
                    rec['max_speed'] = max(rec['max_speed'], speed)

                    # braking 
                    if rec['prev_speed'] is not None:
                        decel = rec['prev_speed'] - speed
                        if decel > 0:
                            rec['sum_decel'] += decel
                            if decel >= SUDDEN_BRAKE_THRESHOLD:
                                rec['sudden_brake_count'] += 1
                                rec['max_decel'] = max(rec['max_decel'], decel)
                    rec['prev_speed'] = speed

                    # lane changes
                    lane = traci.vehicle.getLaneID(vid)
                    if rec['prev_lane'] is not None and lane != rec['prev_lane']:
                        rec['lane_change_count'] += 1
                    rec['prev_lane'] = lane

                    # reached destination y/n
                    if (not rec['reached']
                            and traci.vehicle.getRoadID(vid) == dest):
                        rec['reached'] = True
                        rec['end_step'] = step

            # after stepping get acc waiting time for each vehicle
            for vid, rec in data.items():
                try:
                    rec['wait_time'] = traci.vehicle.getAccumulatedWaitingTime(vid)
                except traci.TraCIException:
                    rec['wait_time'] = 0.0

        finally:
            try:
                traci.close()
            except traci.TraCIException:
                pass

            # get tls metrics
            for agent in agent_manager.agents:
                vid = getattr(agent, 'vehicle_id', None) or getattr(agent, 'vid', None)
                rec = data[vid]
                rec['amber_encountered'] = agent.recorder.amber_encounters
                rec['red_encountered']   = agent.recorder.red_encounters
                rec['amber_run_count']   = agent.recorder.amber_runs
                rec['red_run_count']     = agent.recorder.red_runs

        return data, route_idx
