import os
import time
from src.simulation.simulation_runner import SimulationRunner
from src.agents.agent_manager import AgentManager
from src.metrics.metrics_collector import MetricsCollector
from src.io.csv_exporter import CsvExporter

# Paths & SUMO settings
SUMO_BINARY = "sumo"
SUMO_CONFIG = os.path.join(os.path.dirname(__file__), '..', 'osm_data', 'osm.sumocfg')
CSV_DIR     = os.path.join(os.path.dirname(__file__), 'csv_results')  

def main(num_runs: int = 100):
    runner    = SimulationRunner(SUMO_BINARY, SUMO_CONFIG)
    collector = MetricsCollector()
    exporter  = CsvExporter()

    all_runs: list[tuple[dict, int]] = []
    successful_runs = 0

    for i in range(1, num_runs + 1):
        print(f"\n>>> Starting simulation run {i}/{num_runs}")
        try:
            mgr = AgentManager()
            run_data, route_idx = runner.run(mgr)
            all_runs.append((run_data, route_idx))
            successful_runs += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"[Run {i}] Error occurred: {e}")
            continue

    print(f"\n>>> Completed {successful_runs}/{num_runs} runs successfully.")

    # 1) Detailed per-run CSV
    per_run_rows = []
    for run_idx, (data, route_idx) in enumerate(all_runs, start=1):
        per_run_rows += collector.summarise_run(data, route_idx)
    exporter.to_file(
        os.path.join(CSV_DIR, 'simulation_per_run.csv'),
        headers=[
            'Agent','Route','Time(steps)','Distance(m)','Speed(m/s)','Edges',
            'TLS_enc','TLS_stops','TLS_wait(s)','Amber_enc','AvgWaitTL'
        ],
        rows=per_run_rows
    )

    # 2) Aggregated averages CSV
    avg_rows = collector.compute_averages(all_runs)
    exporter.to_file(
        os.path.join(CSV_DIR, 'simulation_averages.csv'),
        headers=[
            'Agent','AvgTime(steps)','AvgDistance(m)','AvgSpeed(m/s)',
            'AvgEdges','NumRuns','AvgTLS_enc','AvgTLS_stops',
            'AvgTLS_wait(s)','AvgAmber_enc','AvgWaitTL'
        ],
        rows=avg_rows
    )

if __name__ == "__main__":
    main(100)
