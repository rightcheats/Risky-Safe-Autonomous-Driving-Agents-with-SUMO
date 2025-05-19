import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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

    #NEW: single 3×3 heatmap grid of Q-values (rows=phase, cols=speed_bin)
    import seaborn as sns  #NEW: use seaborn for heatmaps
    phases = ['GREEN','AMBER','RED']
    speed_bins = [0,1,2]
    dist_labels = ["0-10","10-20","20-40",">40"]

    speed_labels = {
    0: "Stopped (0 m/s)",
    1: "Slow (0-5 m/s)",
    2: "Cruise (>5 m/s)"
    }   

    fig, axes = plt.subplots(len(phases), len(speed_bins),
                             figsize=(12, 9), sharex=True, sharey=True)
    for i, phase in enumerate(phases):
        for j, speed in enumerate(speed_bins):
            ax = axes[i, j]
            # pivot into distance × actions matrix
            sub = df_q[(df_q.phase == phase) & (df_q.speed_bin == speed)]
            if sub.empty:
                ax.axis('off')
                continue
            pivot = sub.pivot(index='dist_bin', columns='action', values='Q_value')
            # ensure columns in correct order
            pivot = pivot[qt.actions]
            sns.heatmap(pivot, annot=True, fmt=".2f", cbar=(j==len(speed_bins)-1),
                        xticklabels=qt.actions, yticklabels=dist_labels,
                        ax=ax, cmap="viridis")
            if i == 0:
                ax.set_title(speed_labels[speed])
            if j == 0:
                ax.set_ylabel(phase)
            else:
                ax.set_ylabel('')
    fig.suptitle("Q-values Heatmap\n(rows = traffic light phase, columns = speed bin, y = distance bin, x = action)", y=0.92)
    for ax in axes.flat:
        ax.set_xlabel('')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
    plt.tight_layout(rect=[0,0,1,0.90])
    heatmap_path = os.path.join(CSV_DIR, "Q_heatmap_grid.png")  #NEW
    plt.savefig(heatmap_path)  #NEW
    print(f"[Plot] Q-values heatmap grid saved to {heatmap_path}")  #NEW

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
    main(100)
