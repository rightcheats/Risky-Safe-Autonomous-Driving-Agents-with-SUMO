import os
import sys
import traci
from agents.agent_manager import AgentManager

#NOTE: used in earlier versions to test gui/routing

if "SUMO_HOME" not in os.environ:
    sys.exit("SUMO_HOME is not set. Please check your environment variables.")

sumo_binary = "sumo-gui"
sumo_config = os.path.join(os.path.dirname(__file__), "..", "osm_data", "osm.sumocfg")

def run_simulation():
    traci.start([sumo_binary, "-c", sumo_config])
    agent_manager = AgentManager()
    
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
            print("Both agents arrived at destination! :D")
            break

        step += 1

    traci.close()

    print("\n>>> Simulation Results")
    for vid, data in agents.items():
        if data["end_step"] is not None:
            journey_time = data["end_step"] - data["start_step"]
            avg_speed = data["total_distance"] / journey_time if journey_time > 0 else 0
            num_edges = len(data["edges_visited"])
            print(f"\nAgent: {vid}")
            print(f">>> Journey Time: {journey_time} steps")
            print(f">>> Total Distance: {data['total_distance']:.2f} meters")
            print(f">>>Average Speed: {avg_speed:.2f} m/s")
            print(f">>> Edges Travelled: {num_edges}")
        else:
            print(f"\nAgent: {vid} did not reach the destination.")

    print("\n>>> Simulation finished")

if __name__ == "__main__":
    run_simulation()