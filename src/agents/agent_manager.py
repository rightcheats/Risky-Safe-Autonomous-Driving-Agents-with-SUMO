from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver
import traci
import random

class AgentManager:
    def __init__(self):
        self.agents = []

    def get_long_connected_route(self, min_length=5):
        valid_edges = [e for e in traci.edge.getIDList() if not e.startswith(":")]

        # Retry until a valid, long-enough route is found
        while True:
            src = random.choice(valid_edges)
            dest = random.choice(valid_edges)
            if src == dest:
                continue

            route_result = traci.simulation.findRoute(src, dest)
            route_edges = route_result.edges

            if len(route_edges) >= min_length:
                return route_edges, f"route_{src}_{dest}"

    def inject_agents(self):
        # Generate a good route
        route_edges, route_id = self.get_long_connected_route()
        try:
            traci.route.add(route_id, route_edges)
            print(f"Created route '{route_id}' with edges: {route_edges}")
        except Exception as e:
            raise Exception(f"Failed to add route: {e}")

        # Add vehicles with valid lane/speed settings
        safe_id = "safe_1"
        risky_id = "risky_1"
        traci.vehicle.add(safe_id, routeID=route_id, departSpeed="max", departLane="best")
        traci.vehicle.add(risky_id, routeID=route_id, departSpeed="max", departLane="best")
        print(f"Injected vehicles '{safe_id}' and '{risky_id}' on route '{route_id}'.")

        # Set colors for the vehicles to distinguish them
        traci.vehicle.setColor(safe_id, (0, 0, 255))  # Blue color for SafeDriver
        traci.vehicle.setColor(risky_id, (255, 0, 0))  # Red color for RiskyDriver

        # Tie vehicle IDs to your agent classes
        safe_agent = SafeDriver(safe_id, route=route_id)
        risky_agent = RiskyDriver(risky_id, route=route_id)
        self.agents.extend([safe_agent, risky_agent])

    def update_agents(self, step):
        # Risky camera auto-follow
        if step % 10 == 0:  
            if "risky_1" in traci.vehicle.getIDList():
                traci.gui.trackVehicle("View #0", "risky_1")

        # UNCOMMENT TO GET SAFE AUTO-TRACKING
        #if step % 10 == 0:  
        #    if "safe_1" in traci.vehicle.getIDList():
        #        traci.gui.trackVehicle("View #0", "safe_1")        

        for agent in self.agents:
            if agent.vehicle_id in traci.vehicle.getIDList():
                current_route = traci.vehicle.getRoute(agent.vehicle_id)
                print(f"Vehicle '{agent.vehicle_id}' is following route: {current_route}")
                agent.update()
            else:
                print(f"Warning: Vehicle '{agent.vehicle_id}' not in simulation yet.")
