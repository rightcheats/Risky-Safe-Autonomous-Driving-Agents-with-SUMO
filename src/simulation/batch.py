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
SUMO_CONFIG = os.path.join(
    os.path.dirname(__file__),
    "..",
    "osm_data",
    "osm.sumocfg"
)
CSV_DIR = os.path.join(os.path.dirname(__file__), "csv_results")


def main(num_runs: int = 100):
    # ensure output directory exists
    os.makedirs(CSV_DIR, exist_ok=True)

    runner    = SimulationRunner(SUMO_BINARY, SUMO_CONFIG)
    collector = MetricsCollector()
    exporter  = CsvExporter()
    mgr       = AgentManager()

    eps_history_safe   = []
    eps_history_risky  = []
    all_runs           = []
    successful         = 0

    for i in range(1, num_runs + 1):
        print(f"\n>>> Starting simulation run {i}/{num_runs}")
        try:
            run_data, route_idx = runner.run(mgr)
            all_runs.append((run_data, route_idx))
            successful += 1

            # agent-specific exponential decay (no args)
            mgr.decay_exploration()
            eps_history_safe.append(mgr.safe_driver.qtable.epsilon)
            eps_history_risky.append(mgr.risky_driver.qtable.epsilon)

            time.sleep(0.5)
        except Exception as e:
            print(f"[Run {i}] Error: {e}")
            continue

    print(f"\n>>> Completed {successful}/{num_runs} runs.")

    # Plot ε-decay over runs for both drivers
    plt.figure()
    runs = list(range(1, len(eps_history_safe) + 1))
    plt.plot(runs, eps_history_safe,  marker="o", label="SafeDriver")
    plt.plot(runs, eps_history_risky, marker="x", label="RiskyDriver")
    plt.title("Exploration Rate Decay over Runs")
    plt.xlabel("Simulation Run")
    plt.ylabel("ε")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    eps_path = os.path.join(CSV_DIR, "epsilon_decay.png")
    plt.savefig(eps_path)
    print(f"[Plot] ε-decay saved to {eps_path}")

    # build a DataFrame of Q-values for heatmaps
    def build_q_df(qtable):
        records = []
        for (phase, dist_b, speed_b), qvals in qtable.Q.items():
            for action, q in zip(qtable.actions, qvals):
                records.append({
                    "phase": phase,
                    "dist_bin": dist_b,
                    "speed_bin": speed_b,
                    "action": action,
                    "Q_value": q
                })
        return pd.DataFrame(records)

    # SafeDriver heatmap
    qt_safe    = mgr.safe_driver.qtable
    df_q_safe  = build_q_df(qt_safe)

    # RiskyDriver heatmap
    qt_risky   = mgr.risky_driver.qtable
    df_q_risky = build_q_df(qt_risky)

    phases      = ["GREEN", "AMBER", "RED"]
    speed_bins  = [0, 1, 2]
    dist_labels = ["0-10", "10-20", "20-40", ">40"]
    speed_labels = {
        0: "Stopped (0 m/s)",
        1: "Slow (0-5 m/s)",
        2: "Cruise (>5 m/s)"
    }

    def plot_q_heatmap(df_q, qtable, title, out_filename):
        fig, axes = plt.subplots(
            len(phases),
            len(speed_bins),
            figsize=(12, 9),
            sharex=True,
            sharey=True
        )
        for i_phase, phase in enumerate(phases):
            for j_speed, speed in enumerate(speed_bins):
                ax = axes[i_phase, j_speed]
                sub = df_q[
                    (df_q.phase == phase) &
                    (df_q.speed_bin == speed)
                ]
                if sub.empty:
                    ax.axis("off")
                    continue
                pivot = sub.pivot(
                    index="dist_bin",
                    columns="action",
                    values="Q_value"
                )
                pivot = pivot[qtable.actions]
                sns.heatmap(
                    pivot,
                    annot=True,
                    fmt=".2f",
                    cbar=(j_speed == len(speed_bins) - 1),
                    xticklabels=qtable.actions,
                    yticklabels=dist_labels,
                    ax=ax,
                    cmap="viridis"
                )
                if i_phase == 0:
                    ax.set_title(speed_labels[speed])
                if j_speed == 0:
                    ax.set_ylabel(phase)
                else:
                    ax.set_ylabel("")
        fig.suptitle(
            f"{title}\n"
            "(rows = TLS phase, columns = speed bin,\n"
            " y-axis = distance bin, x-axis = action)",
            y=0.92
        )
        for ax in axes.flat:
            ax.set_xlabel("")
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
        plt.tight_layout(rect=[0, 0, 1, 0.90])
        out_path = os.path.join(CSV_DIR, out_filename)
        plt.savefig(out_path)
        print(f"[Plot] {title} saved to {out_path}")

    # Generate and save both heatmaps
    plot_q_heatmap(
        df_q_safe, qt_safe,
        title="SafeDriver Q-Values Heatmap",
        out_filename="Q_heatmap_grid_safe.png"
    )
    plot_q_heatmap(
        df_q_risky, qt_risky,
        title="RiskyDriver Q-Values Heatmap",
        out_filename="Q_heatmap_grid_risky.png"
    )

    # Export per-run CSV
    per_rows = []
    for data, ridx in all_runs:
        per_rows += collector.summarise_run(data, ridx)
    exporter.to_file(
        os.path.join(CSV_DIR, "simulation_per_run.csv"),
        headers=[
            "Agent", "Route", "Time(steps)", "Distance(m)", "Speed(m/s)",
            "MaxSpeed(m/s)", "Edges", "TLS_enc", "Amber_enc", "Red_enc",
            "Amber_runs", "Red_runs", "Sudden_brakes", "MaxDecel(m/s^2)",
            "AvgDecel(m/s^2)", "Lane_changes", "Collisions", "WaitTime(s)"
        ],
        rows=per_rows
    )

    # Export averages CSV
    avg_rows = collector.compute_averages(all_runs)
    exporter.to_file(
        os.path.join(CSV_DIR, "simulation_averages.csv"),
        headers=[
            "Agent", "AvgTime(steps)", "AvgDistance(m)", "AvgSpeed(m/s)",
            "AvgMaxSpeed(m/s)", "AvgEdges", "NumRuns", "AvgTLS_enc",
            "AvgAmber_enc", "AvgRed_enc", "AvgAmber_runs", "AvgRed_runs",
            "AvgSudden_brakes", "AvgMaxDecel(m/s^2)", "AvgAvgDecel(m/s^2)",
            "AvgLane_changes", "AvgCollisions", "AvgWaitTime(s)"
        ],
        rows=avg_rows
    )


if __name__ == "__main__":
    main(100)
