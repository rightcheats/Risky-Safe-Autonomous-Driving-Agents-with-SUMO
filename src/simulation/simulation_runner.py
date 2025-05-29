import traci
import logging

logger = logging.getLogger(__name__)

SUDDEN_BRAKE_THRESHOLD = 3.0

class SimulationRunner:
    """
    - starts SUMO simulation,
    - injects agents, 
    - collects raw per-agent data.
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
                    'green_encountered': 0,
                    'amber_run_count': 0,
                    'red_run_count': 0,
                    'green_run_count': 0,
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
                    'speed_bin_counts': {0: 0, 1: 0, 2: 0, 3: 0}, # for stacked plot
                }

            # simulation loop
            for step in range(self.max_steps):
                traci.simulationStep()
                agent_manager.update_agents(step)

                colliding = traci.simulation.getCollidingVehiclesIDList()
                for vid, rec in data.items():
                    if vid not in traci.vehicle.getIDList():
                        continue

                    # tally current speed bin
                    speed = traci.vehicle.getSpeed(vid) # pick driver by veh id to get  bin logic
                    driver = (agent_manager.safe_driver
                              if vid == agent_manager.safe_driver.vehicle_id
                              else agent_manager.risky_driver)
                    b = driver._speed_bin(speed)
                    
                    logger.debug(
                        "Vehicle %s: Current speed=%.2f m/s, Speed Bin=%d", vid, speed, b)
                    
                    rec['speed_bin_counts'][b] += 1 

                    # collisions
                    if vid in colliding:
                        rec['collision_count'] += 1

                    # distance & edges
                    rec['edges_visited'].add(traci.vehicle.getRoadID(vid))
                    rec['total_distance'] = traci.vehicle.getDistance(vid)

                    # --- TLS STUFF
                    next_tls = traci.vehicle.getNextTLS(vid)
                    seen_ids = set()
                    for tls_id, link_index, dist_raw, *extra in next_tls:
                        dist = float(dist_raw)
                        seen_ids.add(tls_id)

                        # fetch TLS colour string
                        raw_state = traci.trafficlight.getRedYellowGreenState(tls_id).lower()
                        rec['tls_last_state'][tls_id] = raw_state

                        # count first encounter within 10m
                        if dist <= 10.0 and tls_id not in rec['tls_encountered']:
                            rec['tls_encountered'].add(tls_id)
                            if 'y' in raw_state:
                                rec['amber_encountered'] += 1
                            elif 'r' in raw_state:
                                rec['red_encountered'] += 1
                            elif 'g' in raw_state:
                                rec['green_encountered'] += 1

                    passed = set(rec['tls_last_state']) - seen_ids
                    for tls_id in passed:
                        last = rec['tls_last_state'].pop(tls_id)
                        # one run per tls passed based on colour
                        if 'y' in last:
                            rec['amber_run_count'] += 1
                        elif 'r' in last:
                            rec['red_run_count'] += 1
                        elif 'g' in last:
                            rec['green_run_count'] += 1

                    # --- SPEED STUFF
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

        return data, route_idx