import os
import time
import pandas as pd
import matplotlib.pyplot as plt

from src.simulation.simulation_runner import SimulationRunner
from src.agents.agent_manager import AgentManager
from src.metrics.metrics_collector import MetricsCollector
from src.io.csv_exporter import CsvExporter

SUMO_BINARY = "sumo"
SUMO_CONFIG = os.path.join(os.path.dirname(__file__), '..', 'osm_data', 'osm.sumocfg')
CSV_DIR     = os.path.join(os.path.dirname(__file__), 'csv_results')

def main(num_runs: int = 100):
    runner = SimulationRunner(SUMO_BINARY, SUMO_CONFIG)
    collector = MetricsCollector()
    exporter = CsvExporter()

    mgr = AgentManager()
    eps_history = []

    all_runs = []
    successful = 0

    for i in range(1, num_runs + 1):
        print(f"\n>>> Starting simulation run {i}/{num_runs}")
        try:
            run_data, route_idx = runner.run(mgr)
            all_runs.append((run_data, route_idx))
            successful += 1

            # decay eploration after each run safedriver
            mgr.decay_exploration(decay_rate=0.99, min_epsilon=0.05)
            eps_history.append(mgr.safe_driver.qtable.epsilon)

            time.sleep(0.5)
        except Exception as e:
            print(f"[Run {i}] Error: {e}")
            continue

    print(f"\n>>> Completed {successful}/{num_runs} runs.")

    #safedriver epsilon decay over runs 
    plt.figure()
    runs = list(range(1, len(eps_history) + 1))
    plt.plot(runs, eps_history, marker='o')
    plt.title("Exploration Rate Decay over Runs")       
    plt.xlabel("Simulation Run")                        
    plt.ylabel("ε")                                      
    plt.grid(True)
    plt.tight_layout()
    eps_path = os.path.join(CSV_DIR, "epsilon_decay.png")
    plt.savefig(eps_path)
    print(f"[Plot] ε-decay saved to {eps_path}")

    # enumerate final q table
    qt = mgr.safe_driver.qtable
    records = []
    for (phase, dist_b, speed_b), qvals in qt.Q.items():
        for action, q in zip(qt.actions, qvals):
            records.append({
                "phase":       phase,
                "dist_bin":    dist_b,
                "speed_bin":   speed_b,
                "action":      action,
                "Q_value":     q
            })

    df_q = pd.DataFrame(records)

    # NEW: plot Q-values vs distance for each (phase, speed_bin)
    actions = qt.actions
    phases = df_q['phase'].unique()
    speed_bins = sorted(df_q['speed_bin'].unique())

    for phase in phases:
        for speed in speed_bins:
            sub = df_q[(df_q['phase'] == phase) & (df_q['speed_bin'] == speed)]
            if sub.empty:
                continue
            pivot = sub.pivot(index='dist_bin', columns='action', values='Q_value')
            plt.figure()
            for action in actions:
                if action in pivot:
                    plt.plot(pivot.index, pivot[action], marker='o', label=action)
            plt.title(f"Q-values vs Distance — {phase}, speed_bin={speed}")       
            plt.xlabel("Distance Bin")                                           
            plt.ylabel("Q-value")                                                
            plt.xticks([0,1,2,3], ["0–10","10–20","20–40",">40"])                
            plt.legend(title="Action")                                          
            plt.grid(True)                                                      
            plt.tight_layout()                                                  
            qv_path = os.path.join(CSV_DIR, f"Q_{phase}_spd{speed}.png")        
            plt.savefig(qv_path)                                               
            print(f"[Plot] Q-values for {phase}, speed_bin={speed} saved to {qv_path}")  

    # per run csv
    per_rows = []
    for _, (data, ridx) in enumerate(all_runs, start=1):
        per_rows += collector.summarise_run(data, ridx)
    exporter.to_file(
        os.path.join(CSV_DIR, 'simulation_per_run.csv'),
        headers=[
            'Agent', 'Route', 'Time(steps)', 'Distance(m)', 'Speed(m/s)', 'MaxSpeed(m/s)', 'Edges',
            'TLS_enc', 'Amber_enc', 'Red_enc', 'Amber_runs', 'Red_runs',
            'Sudden_brakes', 'MaxDecel(m/s^2)', 'AvgDecel(m/s^2)',
            'Lane_changes', 'Collisions',
            'WaitTime(s)'
        ],
        rows=per_rows
    )

    # averages csv
    avg_rows = collector.compute_averages(all_runs)
    exporter.to_file(
        os.path.join(CSV_DIR, 'simulation_averages.csv'),
        headers=[
            'Agent', 'AvgTime(steps)', 'AvgDistance(m)', 'AvgSpeed(m/s)', 'AvgMaxSpeed(m/s)', 'AvgEdges',
            'NumRuns', 'AvgTLS_enc', 'AvgAmber_enc', 'AvgRed_enc', 'AvgAmber_runs', 'AvgRed_runs',
            'AvgSudden_brakes', 'AvgMaxDecel(m/s^2)', 'AvgAvgDecel(m/s^2)',
            'AvgLane_changes', 'AvgCollisions',
            'AvgWaitTime(s)'
        ],
        rows=avg_rows
    )

if __name__ == "__main__":
    main(10)
