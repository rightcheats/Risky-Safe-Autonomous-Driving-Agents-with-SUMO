import os
import sys
import traci

if "SUMO_HOME" not in os.environ:
    sys.exit("SUMO_HOME is not set. Please check your environment variables.")

sumo_binary = "sumo-gui"
# Update the path to point to the new folder
sumo_config = os.path.join(os.path.dirname(__file__), "sumoScenario", "osm.sumocfg")

def run_simulation():
    traci.start([sumo_binary, "-c", sumo_config])
    for step in range(100):  # Run for 100 simulation steps
        traci.simulationStep()
        vehicles = traci.vehicle.getIDList()
        print(f"Step {step}: Vehicles in simulation - {vehicles}")
    traci.close()
    print("Simulation finished!")

if __name__ == "__main__":
    run_simulation()