import random
import traci
from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver

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
            ("-493711858#1", "-292897032#1"),       
            ("-49797451#0", "-500529199#3"),        
            ("-502509273", "-5067431#0"),           
            ("-5067431#1", "-510234237#1") 
        ]
        self.route_id = None
        self.destination_edge = None

    def inject_agents(self):
        from_edge, to_edge = random.choice(self.valid_routes)
        self.route_id = f"route_{from_edge}_to_{to_edge}"
        self.destination_edge = to_edge

        try:
            traci.route.add(self.route_id, [from_edge, to_edge])
        except traci.TraCIException:
            pass  # Ignore if route already exists

        safe_id = "safe_1"
        risky_id = "risky_1"
        traci.vehicle.add(safe_id, routeID=self.route_id, departSpeed="max", departLane="best")
        traci.vehicle.add(risky_id, routeID=self.route_id, departSpeed="max", departLane="best")
        print(f"Injected agents on route '{self.route_id}' from '{from_edge}' to '{to_edge}'.")

        traci.vehicle.setColor(safe_id, (0, 0, 255))    # Blue
        traci.vehicle.setColor(risky_id, (255, 0, 0))   # Red

        self.agents.append(SafeDriver(safe_id, self.route_id))
        self.agents.append(RiskyDriver(risky_id, self.route_id))

    def update_agents(self, step):
        if step % 10 == 0:
            if "safe_1" in traci.vehicle.getIDList():
                traci.gui.trackVehicle("View #0", "safe_1")

    def get_destination_edge(self):
        return self.destination_edge
