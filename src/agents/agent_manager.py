import random
import traci
from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver

class AgentManager:
    def __init__(self):
        self.agents = []
        self.valid_routes = [
            ("-100306119", "-102745233"),           # A1 → B1
            ("-100306144", "-1040796649#1"),         # A2 → B2
            ("-1051388674#0", "-1052870930"),        # A3 → B3
            ("-1052870931", "-1054937080#1"),         # A4 → B4
            ("-1055385139#1", "-1065099801#1"),        # A5 → B5
            ("-1065099802#1", "-1065201821#0"),        # A6 → B6
            ("-493711858#1", "-292897032#1"),         # A7 → B7
            ("-49797451#0", "-500529199#3"),          # A8 → B8
            ("-502509273", "-5067431#0"),             # A9 → B9
            ("-5067431#1", "-510234237#1")            # A10 → B10
        ]
        self.route_id = None
        self.destination_edge = None

    def validate_route_edges(self, from_edge, to_edge):
        # Retrieve the list of valid edges from SUMO
        valid_edges = traci.edge.getIDList()
        if from_edge not in valid_edges:
            raise Exception(f"Invalid route: start edge '{from_edge}' not found in the network.")
        if to_edge not in valid_edges:
            raise Exception(f"Invalid route: destination edge '{to_edge}' not found in the network.")
        # Optionally, you can print a confirmation:
        print(f"Route validation: '{from_edge}' and '{to_edge}' are valid edges.")

    def inject_agents(self):
        from_edge, to_edge = random.choice(self.valid_routes)
        self.validate_route_edges(from_edge, to_edge)

        self.route_id = f"route_{from_edge}_to_{to_edge}"
        self.destination_edge = to_edge

        # Use SUMO's built-in Dijkstra routing (by letting SUMO compute a route for the two points)
        try:
            traci.route.add(self.route_id, [from_edge, to_edge])
        except traci.TraCIException:
            # If the route already exists this exception might be thrown.
            pass

        safe_id = "safe_1"
        risky_id = "risky_1"
        traci.vehicle.add(safe_id, routeID=self.route_id, departSpeed="max", departLane="best")
        traci.vehicle.add(risky_id, routeID=self.route_id, departSpeed="max", departLane="best")
        print(f"Injected agents on route '{self.route_id}' from '{from_edge}' to '{to_edge}'.")

        traci.vehicle.setColor(safe_id, (0, 0, 255))   # Blue for SafeDriver
        traci.vehicle.setColor(risky_id, (255, 0, 0))   # Red for RiskyDriver

        self.agents.append(SafeDriver(safe_id, self.route_id))
        self.agents.append(RiskyDriver(risky_id, self.route_id))

    def update_agents(self, step):
        if step % 10 == 0:
            if "safe_1" in traci.vehicle.getIDList():
                traci.gui.trackVehicle("View #0", "safe_1")

    def get_destination_edge(self):
        return self.destination_edge
