import random
import logging
import traci
from traci import TraCIException

from .safe_driver import SafeDriver
from .risky_driver import RiskyDriver
from src.simulation.tls_recorder import TLSEventRecorder

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Manages both agents in: 
        - creation 
        - injection 
        - updating 
        - epsilon-decay
    """

    def __init__(self):
        self.agents = []
        self.safe_driver = None
        self.risky_driver = None
        self.valid_routes = [ # manually chose 10 routes that span the map for training
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
        ] #TODO: add more routes? automatic routing? 
        self.chosen_route_index = None
        self.route_id = None
        self.destination_edge = None

    def validate_route_edges(self, from_edge: str, to_edge: str) -> None:
        valid_edges = traci.edge.getIDList()
        if from_edge not in valid_edges or to_edge not in valid_edges:
            raise ValueError(f"Invalid route edges: {from_edge} → {to_edge}")
        logger.info("Route validation passed for %s → %s", from_edge, to_edge)

    def inject_agents(self) -> None:
        self.chosen_route_index = random.randint(1, len(self.valid_routes))
        from_edge, to_edge = self.valid_routes[self.chosen_route_index - 1]
        self.validate_route_edges(from_edge, to_edge)

        self.route_id = f"route_{from_edge}_to_{to_edge}"
        self.destination_edge = to_edge

        try:
            traci.route.add(self.route_id, [from_edge, to_edge])
        except TraCIException:
            pass
        
        safe_id, risky_id = "safe_1", "risky_1"
        for vid, color in ((safe_id, (0, 0, 255)), (risky_id, (255, 0, 0))): # safe = blue, risky = red
            traci.vehicle.add(
                vid,
                routeID=self.route_id,
                departSpeed="max",
                departLane="best",
            )
            traci.vehicle.setColor(vid, color)

        logger.info(
            "Injected agents on %s (route #%d)",
            self.route_id,
            self.chosen_route_index,
        )

        # safedriver instantiation / reuse
        if self.safe_driver is None:
            recorder = TLSEventRecorder()
            self.safe_driver = SafeDriver(safe_id, recorder)
            self.agents.append(self.safe_driver)
        else:
            self.safe_driver.vehicle_id = safe_id
            self.safe_driver.prev_state = None
            self.safe_driver.last_action = None
            self.safe_driver.recorder = TLSEventRecorder()
            self.safe_driver.last_tls_phase = None

        # → load persisted Q-values (if any)
        qpath_safe = r"C:\Users\lolam\Documents\comp sci\y3\y3-spr\IntelAgents\Coursework\project\src\agents\learning\models\safe_driver_qtable.pkl"
        self.safe_driver.qtable.load(qpath_safe)

        # riskydriver instantiation / reuse
        if self.risky_driver is None:
            recorder = TLSEventRecorder()
            self.risky_driver = RiskyDriver(risky_id, self.route_id, recorder)
            self.agents.append(self.risky_driver)
        else:
            self.risky_driver.vehicle_id = risky_id
            self.risky_driver.prev_state = None
            self.risky_driver.last_action = None
            self.risky_driver.recorder = TLSEventRecorder()
            self.risky_driver.last_tls_phase = None

        # → load persisted Q-values for risky driver
        qpath_risky = r"C:\Users\lolam\Documents\comp sci\y3\y3-spr\IntelAgents\Coursework\project\src\agents\learning\models\risky_driver_qtable.pkl"
        self.risky_driver.qtable.load(qpath_risky)

    def update_agents(self, step: int) -> None:
        active = set(traci.vehicle.getIDList())
        for agent in self.agents:
            vid = getattr(agent, "vehicle_id", None)
            if vid in active:
                agent.update()

        # force cam to follow safe, replace with risky_1 if desired
        #TODO: wrap so errors dont keep appearing
        # if step % 10 == 0 and "safe_1" in active:
        #     try:
        #         traci.gui.trackVehicle("View #0", "safe_1")
        #     except TraCIException:
        #         pass

    def get_destination_edge(self) -> str:
        return self.destination_edge

    def get_route_label(self) -> int:
        return self.chosen_route_index

    def decay_exploration(self) -> None:
        """
        Apply agent-specific epsilon-decay schedules:
        - RiskyDriver: epsilon_0 = 0.99 -> epsilon_min = 0.10 over 100 episodes
        - SafeDriver:  epsilon_0 = 0.99 -> epsilon_min = 0.01 over 50 episodes
        Resets each drivers episode memory afterward.
        """
        # targets & horizons
        e0, min_risky, runs_risky = 0.99, 0.10, 100
        _, min_safe, runs_safe = 0.99, 0.01,  50

        # compute decay rates 
        decay_risky = (min_risky / e0) ** (1.0 / runs_risky)
        decay_safe  = (min_safe  / e0) ** (1.0 / runs_safe)

        # riskydriver decay
        old = self.risky_driver.qtable.epsilon
        self.risky_driver.qtable.decay_epsilon(decay_rate=decay_risky,
                                            min_epsilon=min_risky)
        logger.info("RiskyDriver ε: %.4f → %.4f", old,
                    self.risky_driver.qtable.epsilon)
        # reset episode state
        self.risky_driver.prev_state = None
        self.risky_driver.last_action = None

        # safedriver decay
        old = self.safe_driver.qtable.epsilon
        self.safe_driver.qtable.decay_epsilon(decay_rate=decay_safe,
                                            min_epsilon=min_safe)
        logger.info("SafeDriver ε: %.4f → %.4f", old,
                    self.safe_driver.qtable.epsilon)
        # reset episode state
        self.safe_driver.prev_state = None
        self.safe_driver.last_action = None

