# batch.py

import os
import time
from src.simulation.simulation_runner import SimulationRunner
from src.agents.agent_manager import AgentManager
from src.metrics.metrics_collector import MetricsCollector
from src.io.csv_exporter import CsvExporter

SUMO_BINARY = "sumo"
SUMO_CONFIG = os.path.join(os.path.dirname(__file__), '..', 'osm_data', 'osm.sumocfg')
CSV_DIR     = os.path.join(os.path.dirname(__file__), 'csv_results')

def main(num_runs: int = 100):
    runner    = SimulationRunner(SUMO_BINARY, SUMO_CONFIG)
    collector = MetricsCollector()
    exporter  = CsvExporter()

    all_runs = []
    successful = 0

    for i in range(1, num_runs+1):
        print(f"\n>>> Starting simulation run {i}/{num_runs}")
        try:
            mgr = AgentManager()
            run_data, route_idx = runner.run(mgr)
            all_runs.append((run_data, route_idx))
            successful += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"[Run {i}] Error: {e}")
            continue

    print(f"\n>>> Completed {successful}/{num_runs} runs.")

    # 1) per-run
    per_rows = []
    for _, (data, ridx) in enumerate(all_runs, start=1):
        per_rows += collector.summarise_run(data, ridx)
    exporter.to_file(
        os.path.join(CSV_DIR, 'simulation_per_run.csv'),
        headers=[
            'Agent','Route','Time(steps)','Distance(m)','Speed(m/s)','MaxSpeed(m/s)','Edges',
            'TLS_enc','TLS_stops','TLS_wait(s)','Amber_enc','Red_enc',
            'Amber_runs','Red_runs',
            'Sudden_brakes','MaxDecel(m/s^2)','AvgDecel(m/s^2)',
            'AvgWaitTL','Collisions'
        ],
        rows=per_rows
    )

    # 2) averages
    avg_rows = collector.compute_averages(all_runs)
    exporter.to_file(
        os.path.join(CSV_DIR, 'simulation_averages.csv'),
        headers=[
            'Agent','AvgTime(steps)','AvgDistance(m)','AvgSpeed(m/s)','AvgMaxSpeed(m/s)','AvgEdges',
            'NumRuns','AvgTLS_enc','AvgTLS_stops','AvgTLS_wait(s)','AvgAmber_enc','AvgRed_enc',
            'AvgAmber_runs','AvgRed_runs',
            'AvgSudden_brakes','AvgMaxDecel(m/s^2)','AvgAvgDecel(m/s^2)',
            'AvgWaitTL','AvgCollisions'
        ],
        rows=avg_rows
    )

if __name__ == "__main__":
    main(10)
