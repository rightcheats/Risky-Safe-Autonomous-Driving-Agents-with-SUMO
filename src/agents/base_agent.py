class BaseAgent:
    def __init__(self, vehicle_id, route):
        self.vehicle_id = vehicle_id
        self.route = route

    def update(self):
        """Update agent state, is overridden by subclasses."""
        pass