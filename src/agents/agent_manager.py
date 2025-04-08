from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver
import traci

class AgentManager:
    def __init__(self):
        self.agents = []

    def get_static_route(self):
        # Hardcoded edge IDs from SUMO GUI
        start_edge = "-1051388674#0"  # Chosen start edge (A)
        end_edge = "511961981"         # Chosen end edge (B)
        print(f"Static route from {start_edge} to {end_edge}")
        
        # Use SUMO's Dijkstra algorithm to compute the route
        route_result = traci.simulation.findRoute(start_edge, end_edge)
        route_edges = route_result.edges
        
        if not route_edges:
            raise Exception(f"No route found between {start_edge} and {end_edge}")
        
        return route_edges, "static_AB_route"

    def inject_agents(self):
        # Use the computed static route
        route_edges, route_id = self.get_static_route()
        try:
            traci.route.add(route_id, route_edges)
            print(f"Created static route '{route_id}' with edges: {route_edges}")
        except Exception as e:
            raise Exception(f"Failed to add route: {e}")

        # Add vehicles with valid lane/speed settings
        safe_id = "safe_1"
        risky_id = "risky_1"
        traci.vehicle.add(safe_id, routeID=route_id, departSpeed="max", departLane="best")
        traci.vehicle.add(risky_id, routeID=route_id, departSpeed="max", departLane="best")
        print(f"Injected vehicles '{safe_id}' and '{risky_id}' on route '{route_id}'.")

        # Set colors to distinguish the vehicles
        traci.vehicle.setColor(safe_id, (0, 0, 255))   # Blue for SafeDriver
        traci.vehicle.setColor(risky_id, (255, 0, 0))   # Red for RiskyDriver

        # Tie vehicle IDs to your agent classes
        safe_agent = SafeDriver(safe_id, route=route_id)
        risky_agent = RiskyDriver(risky_id, route=route_id)
        self.agents.extend([safe_agent, risky_agent])

    def update_agents(self, step):
        # # Risky driver auto-follow
        # if step % 10 == 0:  
        #     if "risky_1" in traci.vehicle.getIDList():
        #         traci.gui.trackVehicle("View #0", "risky_1")

        # for agent in self.agents:
        #     if agent.vehicle_id in traci.vehicle.getIDList():
        #         current_route = traci.vehicle.getRoute(agent.vehicle_id)
        #         print(f"Vehicle '{agent.vehicle_id}' is following route: {current_route}")
        #         agent.update()
        #     else:
        #         print(f"Warning: Vehicle '{agent.vehicle_id}' not in simulation yet.")

        # Safe driver auto-follow
        if step % 10 == 0:  
            if "safe_1" in traci.vehicle.getIDList():
                traci.gui.trackVehicle("View #0", "safe_1")

        for agent in self.agents:
            if agent.vehicle_id in traci.vehicle.getIDList():
                current_route = traci.vehicle.getRoute(agent.vehicle_id)
                print(f"Vehicle '{agent.vehicle_id}' is following route: {current_route}")
                agent.update()
            else:
                print(f"Warning: Vehicle '{agent.vehicle_id}' not in simulation yet.")
