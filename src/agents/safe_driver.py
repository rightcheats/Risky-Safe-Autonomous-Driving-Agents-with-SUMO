from .base_agent import BaseAgent

class SafeDriver(BaseAgent):
    def update(self):
        print(f"Updating SafeDriver {self.vehicle_id}")