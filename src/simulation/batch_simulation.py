import os
import sys
import traci
import csv
from src.agents.agent_manager import AgentManager

# Check if SUMO_HOME is set correctly
if "SUMO_HOME" not in os.environ:
    sys.exit("SUMO_HOME is not set. Please check your environment variables.")

# Use headless binary (no GUI)
sumo_binary = "sumo"  # switch from "sumo-gui" to headless

# Path to SUMO config
sumo_config = os.path.join(os.path.dirname(__file__), "..", "osm_data", "osm.sumocfg")

def run_simulation():
    # Launch SUMO with optimised flags
    traci.start([
        sumo_binary,
        "-c", sumo_config,
        "--start",                  # auto-start simulation without manual GUI interaction
        "--no-warnings",            # reduce console noise
        "--no-step-log",            # suppress step-by-step logging
        "--quit-on-end"             # auto-close after simulation ends
    ])

    agent_manager = AgentManager()

    # Inject agents after simulation starts to get full network access
    try:
        agent_manager.inject_agents()
    except Exception as e:
        print(f"Route validation failed: {e}")
        traci.close()
        return

    destination_edge = agent_manager.get_destination_edge()

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
            print("Both agents reached the destination.")
            break

        step += 1

    traci.close()

    print("\n=== Simulation Results ===")
    for vid, data in agents.items():
        if data["end_step"] is not None:
            journey_time = data["end_step"] - data["start_step"]
            avg_speed = data["total_distance"] / journey_time if journey_time > 0 else 0
            num_edges = len(data["edges_visited"])
            print(f"\nAgent: {vid}")
            print(f"→ Journey Time: {journey_time} steps")
            print(f"→ Total Distance: {data['total_distance']:.2f} meters")
            print(f"→ Average Speed: {avg_speed:.2f} m/s")
            print(f"→ Edges Travelled: {num_edges}")
        else:
            print(f"\nAgent: {vid} did not reach the destination.")

    return agents


def run_multiple_simulations(num_runs=100):
    # Initialize variables to store cumulative results for each agent
    agent_results = {
        "safe_1": {
            "total_journey_time": 0,
            "total_distance": 0,
            "total_speed": 0,
            "total_edges": 0,
            "reached_count": 0,
        },
        "risky_1": {
            "total_journey_time": 0,
            "total_distance": 0,
            "total_speed": 0,
            "total_edges": 0,
            "reached_count": 0,
        },
    }

    # Run simulations multiple times
    for run_number in range(1, num_runs + 1):
        print(f"Running simulation {run_number}/{num_runs}...")
        agents = run_simulation()  # Run a single simulation
        
        for vid, data in agents.items():
            if data["end_step"] is not None:
                journey_time = data["end_step"] - data["start_step"]
                avg_speed = data["total_distance"] / journey_time if journey_time > 0 else 0
                num_edges = len(data["edges_visited"])
                
                # Accumulate data for averages
                agent_results[vid]["total_journey_time"] += journey_time
                agent_results[vid]["total_distance"] += data["total_distance"]
                agent_results[vid]["total_speed"] += avg_speed
                agent_results[vid]["total_edges"] += num_edges
                agent_results[vid]["reached_count"] += 1
            else:
                print(f"Agent {vid} did not reach the destination in run {run_number}.")

    # Write the averaged results to CSV
    output_path = os.path.join(os.path.dirname(__file__), "simulation_averages.csv")
    with open(output_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        
        # Write header
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

            # Write averaged data for each agent
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
    run_multiple_simulations(100)  # Run 100 simulations and calculate averages
