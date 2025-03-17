import os
import sys
import traci

# Check if SUMO_HOME is set in the sys env var
if "SUMO_HOME" not in os.environ:
    sys.exit("SUMO_HOME is not set. Please check your environment variables.")

# define config and binaries
sumo_binary = "sumo-gui"
sumo_config = os.path.join(os.path.dirname(__file__), "sumoScenario", "osm.sumocfg")

def run_simulation():
    """Starts the SUMO simulation and runs for 100 steps."""
    traci.start([sumo_binary, "-c", sumo_config])
    for step in range(100):  # Run for 100 simulation steps
        traci.simulationStep()
        vehicles = traci.vehicle.getIDList()  # Get list of vehicles in simulation
        print(f"Step {step}: Vehicles in simulation - {vehicles}")
    traci.close()
    print("Simulation finished!")
