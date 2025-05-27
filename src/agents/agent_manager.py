import random
import logging
import traci
import os

from traci import TraCIException
from traci import constants as tc

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
        self.model_dir = os.path.join(os.path.dirname(__file__), "learning", "models")
        self.chosen_route_index = None
        self.route_id = None
        self.destination_edge = None

    def validate_route_edges(self, from_edge: str, to_edge: str) -> None:
        valid_edges = traci.edge.getIDList()
        if from_edge not in valid_edges or to_edge not in valid_edges:
            raise ValueError(f"Invalid route edges: {from_edge} → {to_edge}")
        # logger.info("Route validation passed for %s → %s", from_edge, to_edge)

    def inject_agents(self) -> None:
        
        # pick a valid random route via SUMO’s router, retry up to 100 times
        edges = traci.edge.getIDList()
        start_edge = end_edge = None
        self.route_edges = []

        for _ in range(100):
            a, b = random.sample(edges, 2)
            try:
                candidate = traci.simulation.findRoute(a, b)
            except TraCIException:
                continue
            if len(candidate.edges) > 1:
                start_edge, end_edge = a, b
                self.route_edges = candidate.edges
                break

        # if no valid route found, abort with clear error
        if not self.route_edges:
            raise RuntimeError("Could not find any non-degenerate route in 100 attempts")

        # now register the successful route
        self.route_id        = f"route_{start_edge}_to_{end_edge}"
        self.destination_edge = self.route_edges[-1]
        traci.route.add(self.route_id, self.route_edges)

        safe_id, risky_id = "safe_1", "risky_1"

        # Step 2: instantiate or reset drivers we use max_speed_excess
        if self.safe_driver is None:
            recorder = TLSEventRecorder()
            self.safe_driver = SafeDriver(safe_id, recorder)
            self.agents.append(self.safe_driver)
            # load pretrained SafeDriver Q-table
            safe_path = os.path.join(self.model_dir, "safe_driver_qtable.pkl")
            self.safe_driver.qtable.load(safe_path)
            self.safe_driver.qtable.epsilon = 0.99 # epsilon not loaded = decays
        else:
            self.safe_driver.vehicle_id      = safe_id
            self.safe_driver.prev_state      = None
            self.safe_driver.last_action     = None
            self.safe_driver.recorder        = TLSEventRecorder()
            self.safe_driver.last_tls_phase  = None

        if self.risky_driver is None:
            recorder = TLSEventRecorder()
            self.risky_driver = RiskyDriver(risky_id, self.route_id, recorder)
            self.agents.append(self.risky_driver)
            # load pretrained RiskyDriver Q-table
            risky_path = os.path.join(self.model_dir, "risky_driver_qtable.pkl")
            self.risky_driver.qtable.load(risky_path)
            self.risky_driver.qtable.epsilon = 0.99
        else:
            self.risky_driver.vehicle_id      = risky_id
            self.risky_driver.prev_state      = None
            self.risky_driver.last_action     = None
            self.risky_driver.recorder        = TLSEventRecorder()
            self.risky_driver.last_tls_phase  = None

        def edge_speed(edge_id: str) -> float:
            # 1) edge parameter “speed”
            s = traci.edge.getParameter(edge_id, "speed")
            if s:
                return float(s)
            # 2) fallback: use first lane’s maxSpeed
            num = traci.edge.getLaneNumber(edge_id)
            if num > 0:
                lane0 = f"{edge_id}_0"
                return traci.lane.getMaxSpeed(lane0)
            return 0.0

        route_edges = traci.route.getEdges(self.route_id)
        route_max = max(edge_speed(e) for e in route_edges)
        # logger.info("Route max speed limit across edges: %.2f", route_max)

        for vid, color in ((safe_id, (0, 0, 255)), (risky_id, (255, 0, 0))):
            traci.vehicle.add(
                vid,
                routeID=self.route_id,
                departSpeed="max",
                departLane="best",
            )
            traci.vehicle.setColor(vid, color)

            # choose each agent’s overshoot factor
            factor = (
                self.safe_driver.max_speed_excess
                if vid == safe_id
                else self.risky_driver.max_speed_excess
            )
            new_max = route_max * factor
            traci.vehicle.setMaxSpeed(vid, new_max)
            logger.info(
                "%s maxSpeed bumped: route_max=%.2f → maxSpeed=%.2f",
                vid, route_max, new_max
            )

            # disable speed-limit enforcement (bit 6)
            mode = traci.vehicle.getSpeedMode(vid)
            traci.vehicle.setSpeedMode(vid, 0)

            mode_after = traci.vehicle.getSpeedMode(vid)
            logger.info("%s speed mode set: initial=%s, after=%s",
                        vid, mode, mode_after)


        # logger.info(
        #     "Injected agents on %s (route #%d)",
        #     self.route_id,
        #     self.chosen_route_index,
        # )

    def update_agents(self, step: int) -> None:
        active = set(traci.vehicle.getIDList())
        for agent in self.agents:
            vid = getattr(agent, "vehicle_id", None)
            if vid in active:
                agent.update()

    def get_destination_edge(self) -> str:
        return self.destination_edge

    def get_route_label(self) -> int:
        return self.chosen_route_index

    def decay_exploration(self) -> None:
        """
        Apply agent-specific epsilon-decay schedules:
        - RiskyDriver: epsilon_0 = 0.99 → epsilon_min = 0.10 over 100 episodes
        - SafeDriver:  epsilon_0 = 0.99 → epsilon_min = 0.01 over 50 episodes
        Resets each drivers’ episode state afterward.
        """
        e0, min_risky, runs_risky = 0.99, 0.10, 100
        _, min_safe, runs_safe = 0.99, 0.01,  50

        # compute decay rates
        decay_risky = (min_risky / e0) ** (1.0 / runs_risky)
        decay_safe  = (min_safe  / e0) ** (1.0 / runs_safe)

        # RiskyDriver decay
        old = self.risky_driver.qtable.epsilon
        self.risky_driver.qtable.decay_epsilon(
            decay_rate=decay_risky, min_epsilon=min_risky
        )
        # logger.info("RiskyDriver ε: %.4f → %.4f", old, self.risky_driver.qtable.epsilon)
        self.risky_driver.prev_state  = None
        self.risky_driver.last_action = None

        # SafeDriver decay
        old = self.safe_driver.qtable.epsilon
        self.safe_driver.qtable.decay_epsilon(
            decay_rate=decay_safe, min_epsilon=min_safe
        )
        # logger.info("SafeDriver ε: %.4f → %.4f", old, self.safe_driver.qtable.epsilon)
        self.safe_driver.prev_state  = None
        self.safe_driver.last_action = None
