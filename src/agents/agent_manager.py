import random
import traci
from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver

class AgentManager:
    def __init__(self):
        self.agents = []
        # Predefined routes as a list of tuples (from_edge, to_edge).
        self.valid_routes = [
        ("-100306119", "-102745233"),
        ("-100306144", "-1040796649#1"),
        ("-1051388674#0", "-1052870930"),
        ("-1052870931", "-1054937080#1"),
        ("-1055385139#1", "-1065099801#1"),
        ("-1065099802#1", "-1065201821#0"),
        ("-493711858#1", "23120854#2"),
        ("-49797451#0", "2483868#0"),
        ("584351060", "-5067431#0"),
        ("-5067431#1", "-510234237#1"),           
        ]
        self.route_id = None
        self.destination_edge = None
        self.chosen_route_index = None  # keep track of the selected route (1-10)

    #TODO: remove? now have check_edges.py
    def validate_route_edges(self, from_edge, to_edge):
        valid_edges = traci.edge.getIDList()
        if from_edge not in valid_edges:
            raise Exception(f"Invalid route: start edge '{from_edge}' not found in the network.")
        if to_edge not in valid_edges:
            raise Exception(f"Invalid route: destination edge '{to_edge}' not found in the network.")
        print(f"Route validation: '{from_edge}' and '{to_edge}' are valid edges.")

    def inject_agents(self):
        # select random route from list
        self.chosen_route_index = random.randint(1, len(self.valid_routes))  # 1-based label
        from_edge, to_edge = self.valid_routes[self.chosen_route_index - 1]
        self.validate_route_edges(from_edge, to_edge)

        self.route_id = f"route_{from_edge}_to_{to_edge}"
        self.destination_edge = to_edge

        try:
            traci.route.add(self.route_id, [from_edge, to_edge])
        except traci.TraCIException:
            pass

        safe_id = "safe_1"
        risky_id = "risky_1"
        traci.vehicle.add(safe_id, routeID=self.route_id, departSpeed="max", departLane="best")
        traci.vehicle.add(risky_id, routeID=self.route_id, departSpeed="max", departLane="best")
        print(f"Injected agents on route '{self.route_id}' from '{from_edge}' to '{to_edge}' (Route {self.chosen_route_index}).")

        traci.vehicle.setColor(safe_id, (0, 0, 255))
        traci.vehicle.setColor(risky_id, (255, 0, 0))

        self.agents.append(SafeDriver(safe_id, self.route_id))
        self.agents.append(RiskyDriver(risky_id, self.route_id))

    def update_agents(self, step):
        # cam view, change to risky_1 if needed
        if step % 10 == 0 and "safe_1" in traci.vehicle.getIDList():
            if traci.hasGUI():
                traci.gui.trackVehicle("View #0", "safe_1")

    # track whether reach destination
    def get_destination_edge(self):
        return self.destination_edge

    # track which route
    def get_route_label(self):
        return self.chosen_route_index
    
    # track collisions
    def get_collisions(self):
        return self.collisions