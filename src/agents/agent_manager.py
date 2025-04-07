from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver
import traci

class AgentManager:
    def __init__(self):
        self.agents = []

    def inject_agents(self):
        # Retrieve available edges in the network
        edge_ids = traci.edge.getIDList()
        if len(edge_ids) < 2:
            raise Exception("Not enough edges available to create a route.")

        # For a simple test, select the first two edges as a route.
        # (Make sure these edges are actually connected in your network.)
        new_route = "agent_route"
        route_edges = [edge_ids[0], edge_ids[1]]
        try:
            traci.route.add(new_route, route_edges)
            print(f"Created new route '{new_route}' with edges: {route_edges}")
        except Exception as e:
            raise Exception(f"Failed to add route: {e}")

        # Use the newly created route for the agents.
        safe_id = "safe_1"
        risky_id = "risky_1"
        traci.vehicle.add(safe_id, routeID=new_route)
        traci.vehicle.add(risky_id, routeID=new_route)
        print(f"Injected vehicles '{safe_id}' and '{risky_id}' using route '{new_route}'.")

        # Create agent instances tied to the vehicle IDs.
        safe_agent = SafeDriver(safe_id, route=new_route)
        risky_agent = RiskyDriver(risky_id, route=new_route)
        self.agents.extend([safe_agent, risky_agent])

    def update_agents(self):
        for agent in self.agents:
            if agent.vehicle_id in traci.vehicle.getIDList():
                current_route = traci.vehicle.getRoute(agent.vehicle_id)
                print(f"Vehicle '{agent.vehicle_id}' is following route: {current_route}")
                agent.update()
            else:
                print(f"Warning: Vehicle '{agent.vehicle_id}' not in simulation yet.")

