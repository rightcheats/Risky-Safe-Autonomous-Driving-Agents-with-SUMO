import random
import traci
from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver

class AgentManager:
    def __init__(self):
        self.agents = []
        # Predefined from_edge → to_edge route list
        self.valid_routes = [
            ("-100306119", "-102745233"),
            ("-100306144", "-1040796649#1"),
            # …etc…
        ]
        self.route_id = None
        self.destination_edge = None
        self.chosen_route_index = None

    def validate_route_edges(self, from_edge, to_edge):
        valid_edges = traci.edge.getIDList()
        if from_edge not in valid_edges or to_edge not in valid_edges:
            raise Exception(f"Invalid route edges: {from_edge} → {to_edge}")
        print(f"Route validation passed for {from_edge} → {to_edge}")

    def inject_agents(self):
        # Select a random predefined route
        self.chosen_route_index = random.randint(1, len(self.valid_routes))
        from_edge, to_edge = self.valid_routes[self.chosen_route_index - 1]
        self.validate_route_edges(from_edge, to_edge)

        self.route_id = f"route_{from_edge}_to_{to_edge}"
        self.destination_edge = to_edge

        try:
            traci.route.add(self.route_id, [from_edge, to_edge])
        except traci.TraCIException:
            pass

        # Create vehicles
        safe_id = "safe_1"
        risky_id = "risky_1"
        traci.vehicle.add(safe_id,  routeID=self.route_id, departSpeed="max", departLane="best")
        traci.vehicle.add(risky_id, routeID=self.route_id, departSpeed="max", departLane="best")
        traci.vehicle.setColor(safe_id,  (0,   0, 255))
        traci.vehicle.setColor(risky_id, (255, 0,   0))
        print(f"Injected agents on {self.route_id} (route #{self.chosen_route_index})")

        # Instantiate agent wrappers
        self.agents.append(SafeDriver(safe_id,  self.route_id))
        self.agents.append(RiskyDriver(risky_id, self.route_id))

    def update_agents(self, step: int):
        # 1) First, let each agent apply its driving logic
        for agent in self.agents:
            agent.update()

        # 2) Every 10 steps, if GUI is active, track the safe driver
        if step % 10 == 0 and "safe_1" in traci.vehicle.getIDList():
            if traci.hasGUI():
                traci.gui.trackVehicle("View #0", "safe_1")

    def get_destination_edge(self):
        return self.destination_edge

    def get_route_label(self):
        return self.chosen_route_index
