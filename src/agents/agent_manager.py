import random
import traci
from traci import TraCIException
from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver
from src.simulation.tls_recorder import TLSEventRecorder

class AgentManager:
    def __init__(self):
        self.agents = []
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
        self.chosen_route_index = None

    def validate_route_edges(self, from_edge, to_edge):
        valid_edges = traci.edge.getIDList()
        if from_edge not in valid_edges or to_edge not in valid_edges:
            raise Exception(f"Invalid route edges: {from_edge} → {to_edge}")
        print(f"Route validation passed for {from_edge} → {to_edge}")

    def inject_agents(self):
        self.chosen_route_index = random.randint(1, len(self.valid_routes))
        from_edge, to_edge = self.valid_routes[self.chosen_route_index - 1]
        self.validate_route_edges(from_edge, to_edge)

        self.route_id = f"route_{from_edge}_to_{to_edge}"
        self.destination_edge = to_edge

        try:
            traci.route.add(self.route_id, [from_edge, to_edge])
        except traci.TraCIException:
            pass

        # Create SUMO vehicles
        safe_id = "safe_1"
        risky_id = "risky_1"
        traci.vehicle.add(safe_id,  routeID=self.route_id, departSpeed="max", departLane="best")
        traci.vehicle.add(risky_id, routeID=self.route_id, departSpeed="max", departLane="best")
        traci.vehicle.setColor(safe_id,  (0,   0, 255))
        traci.vehicle.setColor(risky_id, (255, 0,   0))
        print(f"Injected agents on {self.route_id} (route #{self.chosen_route_index})")

        # Instantiate TLS recorders and wrap in driver logic
        safe_recorder = TLSEventRecorder()
        risky_recorder = TLSEventRecorder()
        self.agents.append(SafeDriver(safe_id,  safe_recorder))
        self.agents.append(RiskyDriver(risky_id, self.route_id, risky_recorder))

    def update_agents(self, step: int):
        active = set(traci.vehicle.getIDList())
        for agent in self.agents:
            vid = getattr(agent, 'vehicle_id', None) or getattr(agent, 'vid', None)
            if vid in active:
                agent.update()

        # 2) Every 10 steps, try tracking the safe vehicle in the GUI,
        #    but ignore if we're running headless or the vehicle has gone.
        if step % 10 == 0 and "safe_1" in traci.vehicle.getIDList():
            try:
                traci.gui.trackVehicle("View #0", "safe_1")
            except traci.TraCIException:
                # GUI not available or vehicle has gone—ignore
                pass

    def get_destination_edge(self):
        return self.destination_edge

    def get_route_label(self):
        return self.chosen_route_index
