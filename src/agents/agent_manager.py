# src/agents/agent_manager.py

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
    Manages creation, injection, updating, and exploration‐decay
    for SafeDriver and RiskyDriver agents in the SUMO simulation.
    """

    def __init__(self):
        self.agents = []
        self.safe_driver = None
        self.risky_driver = None
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
        self.chosen_route_index = None
        self.route_id = None
        self.destination_edge = None

    def validate_route_edges(self, from_edge: str, to_edge: str) -> None:
        valid_edges = traci.edge.getIDList()
        if from_edge not in valid_edges or to_edge not in valid_edges:
            raise ValueError(f"Invalid route edges: {from_edge} → {to_edge}")
        logger.info("Route validation passed for %s → %s", from_edge, to_edge)

    def inject_agents(self) -> None:
        # Pick and validate a random route
        self.chosen_route_index = random.randint(1, len(self.valid_routes))
        from_edge, to_edge = self.valid_routes[self.chosen_route_index - 1]
        self.validate_route_edges(from_edge, to_edge)

        self.route_id = f"route_{from_edge}_to_{to_edge}"
        self.destination_edge = to_edge

        try:
            traci.route.add(self.route_id, [from_edge, to_edge])
        except TraCIException:
            pass

        # Add two SUMO vehicles
        safe_id, risky_id = "safe_1", "risky_1"
        for vid, color in ((safe_id, (0, 0, 255)), (risky_id, (255, 0, 0))):
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

        # SafeDriver instantiation / reuse
        if self.safe_driver is None:
            recorder = TLSEventRecorder()
            self.safe_driver = SafeDriver(safe_id, recorder)
            self.agents.append(self.safe_driver)
        else:
            # reuse existing instance, reset only episode-specific state & recorder
            self.safe_driver.vehicle_id  = safe_id
            self.safe_driver.prev_state  = None
            self.safe_driver.last_action = None
            self.safe_driver.recorder    = TLSEventRecorder()

        # RiskyDriver instantiation / reuse
        if self.risky_driver is None:
            recorder = TLSEventRecorder()
            self.risky_driver = RiskyDriver(risky_id, self.route_id, recorder)
            self.agents.append(self.risky_driver)
        else:
            # reuse existing instance, reset only episode-specific state & recorder
            self.risky_driver.vehicle_id  = risky_id
            self.risky_driver.prev_state  = None
            self.risky_driver.last_action = None
            self.risky_driver.recorder    = TLSEventRecorder()

    def update_agents(self, step: int) -> None:
        active = set(traci.vehicle.getIDList())
        for agent in self.agents:
            vid = getattr(agent, "vehicle_id", None)
            if vid in active:
                agent.update()

        # Try to keep the GUI focused on the safe agent every 10 steps
        if step % 10 == 0 and "safe_1" in active:
            try:
                traci.gui.trackVehicle("View #0", "safe_1")
            except TraCIException:
                pass

    def get_destination_edge(self) -> str:
        return self.destination_edge

    def get_route_label(self) -> int:
        return self.chosen_route_index

    def decay_exploration(
        self, decay_rate: float = 0.99, min_epsilon: float = 0.01
    ) -> None:
        """
        Apply ε-decay to both safe and risky drivers and reset their
        episode-specific memory.
        """
        for driver in (self.safe_driver, self.risky_driver):
            if driver and hasattr(driver, "qtable"):
                old_eps = driver.qtable.epsilon
                driver.qtable.epsilon = max(min_epsilon, old_eps * decay_rate)
                driver.prev_state  = None
                driver.last_action = None
                logger.info(
                    "Epsilon decayed for %s: %.3f → %.3f",
                    driver.__class__.__name__,
                    old_eps,
                    driver.qtable.epsilon,
                )
