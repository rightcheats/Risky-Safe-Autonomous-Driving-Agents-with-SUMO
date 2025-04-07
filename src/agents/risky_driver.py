from .base_agent import BaseAgent

class RiskyDriver(BaseAgent):
    def update(self):
        # Placeholder for risky driving logic
        print(f"Updating RiskyDriver {self.vehicle_id}")
        # e.g., implement aggressive maneuvers using traci.vehicle API