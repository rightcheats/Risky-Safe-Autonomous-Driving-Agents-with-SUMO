import os
import sys
import traci

# check env var set
if "SUMO_HOME" not in os.environ:
    sys.exit("SUMO_HOME is not set. Please check your environment variables.")

#define config and binary
sumo_binary = "sumo-gui"
sumo_config = os.path.join(os.path.dirname(__file__), "sumoScenario", "osm.sumocfg")

def run_simulation():
    traci.start([sumo_binary, "-c", sumo_config])
    for step in range(100):  # run for 100 simulation steps
        traci.simulationStep()
        vehicles = traci.vehicle.getIDList() # get list of vehicles in simulation
        print(f"Step {step}: Vehicles in simulation - {vehicles}")
    traci.close()
    print("Simulation finished!") # print vehicle ids for each step

if __name__ == "__main__":
    run_simulation()