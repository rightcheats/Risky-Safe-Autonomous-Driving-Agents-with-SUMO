import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path

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

    os.makedirs(CSV_DIR, exist_ok=True)

    runner = SimulationRunner(SUMO_BINARY, SUMO_CONFIG)
    collector = MetricsCollector()
    exporter = CsvExporter()
    mgr = AgentManager()
    
    eps_history_safe = []
    eps_history_risky = []
    all_runs = []
    successful = 0

    for i in range(1, num_runs + 1):
        print(f"\n>>> Starting simulation run {i}/{num_runs}")
        try:
            run_data, route_idx = runner.run(mgr)
            all_runs.append((run_data, route_idx))
            successful += 1

            # agent-specific exponential decay
            mgr.decay_exploration()
            eps_history_safe.append(mgr.safe_driver.qtable.epsilon)
            eps_history_risky.append(mgr.risky_driver.qtable.epsilon)

            time.sleep(0.5)
        except Exception as e:
            print(f"[Run {i}] Error: {e}")
            continue

    print(f"\n>>> Completed {successful}/{num_runs} runs.")

    # FIGURE: epsilon-decay over runs for both drivers
    plt.figure()
    runs = list(range(1, len(eps_history_safe) + 1))
    plt.plot(runs, eps_history_safe,  marker="o", label="SafeDriver")
    plt.plot(runs, eps_history_risky, marker="x", label="RiskyDriver")
    plt.title("Exploration Rate Decay over Runs")
    plt.xlabel("Simulation Run")
    plt.ylabel("ε (epsilon)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    eps_path = os.path.join(CSV_DIR, "epsilon_decay.png")
    plt.savefig(eps_path)
    print(f"[Plot] epsilon-decay saved to {eps_path}")

    # --- FIGURE: heatmaps for q values per agent 
    # dataframe of q values for heatmap
    def build_q_df(qtable):
        records = []
        for (phase, dist_b, speed_b, _ttl_b), qvals in qtable.Q.items():
            for action, q in zip(qtable.actions, qvals):
                records.append({
                    "phase":    phase,
                    "dist_bin": dist_b,
                    "speed_bin": speed_b,
                    "action":   action,
                    "Q_value":  q
                })

        df = pd.DataFrame(records)
        df = df.groupby(
            ["phase", "dist_bin", "speed_bin", "action"],
            as_index=False
        )["Q_value"].mean()

        return df


    qt_safe = mgr.safe_driver.qtable
    df_q_safe = build_q_df(qt_safe)

    qt_risky = mgr.risky_driver.qtable
    df_q_risky = build_q_df(qt_risky)

    # → persist learned Q-values
    model_dir = Path("src/agents/learning/models")
    safe_path = model_dir / "safe_driver_qtable.pkl"
    risky_path = model_dir / "risky_driver_qtable.pkl"
    mgr.safe_driver.qtable.save(safe_path)
    mgr.risky_driver.qtable.save(risky_path)
    print(f"[Save] Q-tables saved to {model_dir}")

    phases = ["GREEN", "AMBER", "RED"]
    speed_bins = [0, 1, 2]
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
        fig.suptitle( #TODO: change this to be better names?
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

    # export csvs
    per_rows = []
    for data, ridx in all_runs:
        per_rows += collector.summarise_run(data, ridx)
    exporter.to_file(
        os.path.join(CSV_DIR, "simulation_per_run.csv"),
        headers=[
            "Agent", "Route", "Time(steps)", "Distance(m)", "Speed(m/s)",
            "MaxSpeed(m/s)", "Edges", "TLS_enc", "Amber_enc", "Red_enc", "Green_enc",
            "Amber_runs", "Red_runs", "Green_runs", "Sudden_brakes", "MaxDecel(m/s^2)",
            "AvgDecel(m/s^2)", "Lane_changes", "Collisions", "WaitTime(s)"
        ],
        rows=per_rows
    )
    avg_rows = collector.compute_averages(all_runs)
    exporter.to_file(
        os.path.join(CSV_DIR, "simulation_averages.csv"),
        headers=[
            "Agent", "AvgTime(steps)", "AvgDistance(m)", "AvgSpeed(m/s)",
            "AvgMaxSpeed(m/s)", "AvgEdges", "NumRuns", "AvgTLS_enc",
            "AvgAmber_enc", "AvgRed_enc", "AvgGreen_enc", "AvgAmber_runs", "AvgRed_runs",
            "AvgGreen_runs", "AvgSudden_brakes", "AvgMaxDecel(m/s^2)", "AvgAvgDecel(m/s^2)",
            "AvgLane_changes", "AvgCollisions", "AvgWaitTime(s)",
            "TotalTLS_enc", "TotalAmber_enc", "TotalRed_enc", "TotalGreen_enc"
        ],
        rows=avg_rows
    )

    # --- Compare average distribution over first vs last 10 runs per agent ---
    # determine group size (use 10 or half of runs if fewer)
    pct = 0.10
    group_size = max(1, int(successful * pct))
    first_group = all_runs[:group_size]
    last_group  = all_runs[-group_size:]

    agents = [
        mgr.safe_driver.vehicle_id,
        mgr.risky_driver.vehicle_id
    ]
    bin_labels = {
        0: "Stopped",
        1: "Compliant",
        2: "Small overshoot",
        3: "Large overshoot"
    }

    for agent_id in agents:
        # aggregate counts over first and last groups
        agg_first = {
            b: sum(run_data[agent_id]['speed_bin_counts'][b] for run_data, _ in first_group)
            for b in bin_labels
        }
        agg_last = {
            b: sum(run_data[agent_id]['speed_bin_counts'][b] for run_data, _ in last_group)
            for b in bin_labels
        }
        tot_first = sum(agg_first.values()) or 1
        tot_last  = sum(agg_last.values())  or 1

        # build DataFrame of fractions
        df_cmp = pd.DataFrame({
            "Group": [f"Avg of First {int(pct*100)}%  Runs", f"Avg of Last {int(pct*100)}% Runs"],
            **{
                bin_labels[b]: [
                    agg_first[b] / tot_first,
                    agg_last[b]  / tot_last
                ] for b in sorted(bin_labels)
            }
        }).set_index("Group")

        # plot stacked-bar comparison
        fig, ax = plt.subplots(figsize=(8, 4))
        df_cmp.plot(
            kind="bar",
            stacked=True,
            ax=ax,
            legend=True
        )
        fig.suptitle(
            f"{agent_id}: Avg Speed-Bin Distribution\n",
            y=0.95
        )
        ax.set_ylabel("Fraction of Timesteps")
        ax.set_ylim(0, 1)
        plt.xticks(rotation=0)
        plt.tight_layout()
        fig.subplots_adjust(top=0.88)

        out_fname = f"speed_bins_compare_{agent_id}.png"
        out_path  = os.path.join(CSV_DIR, out_fname)
        plt.savefig(out_path)
        print(f"[Plot] avg speed-bin comparison ({group_size}) for {agent_id} saved to {out_path}")

if __name__ == "__main__":
    main(300)