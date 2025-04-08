import os
import sys
import traci
from agents.agent_manager import AgentManager

if "SUMO_HOME" not in os.environ:
    sys.exit("SUMO_HOME is not set. Please check your environment variables.")

sumo_binary = "sumo-gui"
sumo_config = os.path.join(os.path.dirname(__file__), "..", "osm_data", "osm.sumocfg")

def run_simulation():
    traci.start([sumo_binary, "-c", sumo_config])
    agent_manager = AgentManager()
    agent_manager.inject_agents()

    destination_edge = "511961981"

    # Store agent info
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

    for step in range(300):
        traci.simulationStep()
        agent_manager.update_agents(step)

        active_vehicles = traci.vehicle.getIDList()

        for vid in agents.keys():
            if vid in active_vehicles:
                current_edge = traci.vehicle.getRoadID(vid)
                agents[vid]["edges_visited"].add(current_edge)

                # Track distance traveled
                distance = traci.vehicle.getDistance(vid)
                agents[vid]["total_distance"] = distance  # Overwrites with cumulative dist

                if current_edge == destination_edge and not agents[vid]["reached"]:
                    agents[vid]["end_step"] = step
                    agents[vid]["reached"] = True

            elif not agents[vid]["reached"]:
                # If vehicle is no longer active but hasn't been marked as reached
                agents[vid]["end_step"] = step
                agents[vid]["reached"] = True

        # End sim if both finished
        if all(agent["reached"] for agent in agents.values()):
            break

    traci.close()

    print("\n=== Simulation Results ===")
    for vid, data in agents.items():
        journey_time = data["end_step"] - data["start_step"]
        avg_speed = data["total_distance"] / journey_time if journey_time > 0 else 0
        num_edges = len(data["edges_visited"])

        print(f"\nAgent: {vid}")
        print(f"→ Journey Time: {journey_time} steps")
        print(f"→ Total Distance: {data['total_distance']:.2f} meters")
        print(f"→ Average Speed: {avg_speed:.2f} m/s")
        print(f"→ Edges Travelled: {num_edges}")

    print("\nSimulation finished!")

if __name__ == "__main__":
    run_simulation()
