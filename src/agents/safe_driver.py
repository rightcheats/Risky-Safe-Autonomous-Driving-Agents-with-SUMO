import os
import pickle
import random
from collections import defaultdict
import traci

class SafeDriver:
    def __init__(self, vehicle_id: str, epsilon=0.1, alpha=0.5, gamma=0.9):
        self.vehicle_id = vehicle_id
        self.epsilon = epsilon  # exploration factor
        self.alpha = alpha      # learning rate
        self.gamma = gamma      # discount factor
        self.q_table = defaultdict(lambda: {'stop': 0.0, 'proceed': 0.0})
        self.prev_state = None
        self.prev_action = None
        self.qtable_path = f"safe_driver_qtable_{vehicle_id}.pkl"
        self.load_q_table()

    def choose_action(self, state: tuple) -> str:
        if random.random() < self.epsilon:
            return random.choice(['stop', 'proceed'])
        return max(self.q_table[state], key=self.q_table[state].get)

    def update(self, step: int):
        tls_info = traci.vehicle.getNextTLS(self.vehicle_id)
        if not tls_info:
            return  # No TLS ahead

        tls_id, state, dist, _ = tls_info[0]
        if dist > 30:
            return  # TLS too far

        light_state = str(state).lower()
        if 'y' not in light_state:
            return  # Not amber

        # Define state and choose action
        speed = traci.vehicle.getSpeed(self.vehicle_id)
        state_tuple = (round(dist), round(speed))
        action = self.choose_action(state_tuple)

        # Perform action
        if action == 'stop':
            traci.vehicle.setSpeed(self.vehicle_id, 0.0)
        else:
            traci.vehicle.setSpeed(self.vehicle_id, traci.vehicle.getAllowedSpeed(self.vehicle_id))

        # Assign reward (example logic)
        reward = -1 if action == 'proceed' else 1  # Penalize running amber

        # Q-learning update
        if self.prev_state is not None:
            prev_q = self.q_table[self.prev_state][self.prev_action]
            future_q = max(self.q_table[state_tuple].values())
            new_q = prev_q + self.alpha * (reward + self.gamma * future_q - prev_q)
            self.q_table[self.prev_state][self.prev_action] = new_q

        self.prev_state = state_tuple
        self.prev_action = action

        # Logging
        print(f"[SafeDriver] Step {step} — State: {state_tuple}, Action: {action}, Reward: {reward:.2f}")

        if step % 100 == 0:
            print(f"\n[SafeDriver] Q-table snapshot at step {step}:")
            for s, acts in list(self.q_table.items())[:5]:  # limit output
                print(f"  State {s}: {acts}")

        # Save Q-table every time we update (or only when agent reaches destination in full impl)
        self.save_q_table()

    def save_q_table(self):
        with open(self.qtable_path, 'wb') as f:
            pickle.dump(dict(self.q_table), f)

    def load_q_table(self):
        if os.path.exists(self.qtable_path):
            with open(self.qtable_path, 'rb') as f:
                self.q_table = defaultdict(lambda: {'stop': 0.0, 'proceed': 0.0}, pickle.load(f))