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

    for step in range(300):  # Run for 100 simulation steps
        traci.simulationStep()
        agent_manager.update_agents(step)  # Pass step to update_agents

    traci.close()
    print("Simulation finished!")