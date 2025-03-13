import traci
import sumolib

#TODO: do simulation to test
def run_sumo_simulation():
    # TODO: replace path 
    sumo_config_file = "path"

    # starts the sump simulation
    traci.start([sumolib.checkBinary('sumo'), "-c", sumo_config_file])

    # run simulation for 100 steps
    for step in range(100):
        traci.simulationStep()
        print(f"Step: {step} - Vehicle Count: {traci.vehicle.getIDList()}")

    # close simulation
    traci.close()

if __name__ == "__main__":
    run_sumo_simulation()