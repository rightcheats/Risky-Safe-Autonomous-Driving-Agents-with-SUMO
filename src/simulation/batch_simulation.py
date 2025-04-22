import os
import sys
import traci
import csv
from src.agents.agent_manager import AgentManager

if "SUMO_HOME" not in os.environ:
    sys.exit("SUMO_HOME is not set. Please check your environment variables.")

sumo_binary = "sumo"  # headless
sumo_config = os.path.join(os.path.dirname(__file__), "..", "osm_data", "osm.sumocfg")

def run_simulation(run_number=1):
    traci.start([
        sumo_binary,
        "-c", sumo_config,
        "--start",
        "--no-warnings",
        "--no-step-log",
        "--quit-on-end"
    ])

    agent_manager = AgentManager()

    try:
        agent_manager.inject_agents()
    except Exception as e:
        print(f"Route validation failed: {e}")
        traci.close()
        return None, None

    destination_edge = agent_manager.get_destination_edge()
    route_index = agent_manager.get_route_label()

    agents = {
        "safe_1": {
            "reached": False,
            "start_step": 0,
            "end_step": None,
            "total_distance": 0.0,
            "edges_visited": set(),
        },
        "risky_1": {
            "reached": False,
            "start_step": 0,
            "end_step": None,
            "total_distance": 0.0,
            "edges_visited": set(),
        },
    }

    max_steps = 3000
    step = 0

    while step < max_steps:
        traci.simulationStep()
        agent_manager.update_agents(step)

        active_vehicles = traci.vehicle.getIDList()
        for vid in agents:
            if vid in active_vehicles:
                current_edge = traci.vehicle.getRoadID(vid)
                agents[vid]["edges_visited"].add(current_edge)
                agents[vid]["total_distance"] = traci.vehicle.getDistance(vid)
                if current_edge == destination_edge and not agents[vid]["reached"]:
                    agents[vid]["end_step"] = step
                    agents[vid]["reached"] = True

        if all(agents[vid]["reached"] for vid in agents):
            break

        step += 1

    traci.close()
    return agents, route_index

def run_multiple_simulations(num_runs=100):
    agent_results = {
        "safe_1": {"total_journey_time": 0, "total_distance": 0, "total_speed": 0, "total_edges": 0, "reached_count": 0},
        "risky_1": {"total_journey_time": 0, "total_distance": 0, "total_speed": 0, "total_edges": 0, "reached_count": 0},
    }

    # File for detailed per-run results
    detailed_path = os.path.join(os.path.dirname(__file__), "simulation_per_run.csv")
    with open(detailed_path, mode="w", newline="") as f_detail:
        writer_detail = csv.writer(f_detail)
        writer_detail.writerow(["Run", "Agent ID", "Route Index", "Journey Time", "Distance", "Average Speed", "Edges Travelled", "Reached Destination"])

        for run_number in range(1, num_runs + 1):
            print(f"Running simulation {run_number}/{num_runs}...")
            agents, route_index = run_simulation(run_number)

            if agents is None:
                print(f"Run {run_number} failed to start properly.")
                continue

            for vid, data in agents.items():
                if data["end_step"] is not None:
                    journey_time = data["end_step"] - data["start_step"]
                    avg_speed = data["total_distance"] / journey_time if journey_time > 0 else 0
                    num_edges = len(data["edges_visited"])

                    agent_results[vid]["total_journey_time"] += journey_time
                    agent_results[vid]["total_distance"] += data["total_distance"]
                    agent_results[vid]["total_speed"] += avg_speed
                    agent_results[vid]["total_edges"] += num_edges
                    agent_results[vid]["reached_count"] += 1

                    writer_detail.writerow([
                        run_number, vid, route_index, journey_time,
                        round(data["total_distance"], 2),
                        round(avg_speed, 2),
                        num_edges, "Yes"
                    ])
                else:
                    writer_detail.writerow([run_number, vid, route_index, "-", "-", "-", "-", "No"])

    print("Detailed results saved to simulation_per_run.csv")

    # File for overall averages
    average_path = os.path.join(os.path.dirname(__file__), "simulation_averages.csv")
    with open(average_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Agent ID", "Average Journey Time (steps)", "Average Distance (m)", "Average Speed (m/s)", "Average Edges Travelled", "Reaches Destination Count"])

        for vid in agent_results:
            total_runs = agent_results[vid]["reached_count"]
            if total_runs > 0:
                avg_journey_time = agent_results[vid]["total_journey_time"] / total_runs
                avg_distance = agent_results[vid]["total_distance"] / total_runs
                avg_speed = agent_results[vid]["total_speed"] / total_runs
                avg_edges = agent_results[vid]["total_edges"] / total_runs
            else:
                avg_journey_time = avg_distance = avg_speed = avg_edges = 0

            writer.writerow([
                vid,
                round(avg_journey_time, 2),
                round(avg_distance, 2),
                round(avg_speed, 2),
                round(avg_edges, 2),
                total_runs
            ])

    print("Averaged results saved to simulation_averages.csv")

if __name__ == "__main__":
    run_multiple_simulations(100)
