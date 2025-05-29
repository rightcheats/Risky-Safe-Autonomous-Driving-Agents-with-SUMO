# test waiting times metric collection

import pytest
from src.simulation.batch import main                     
from src.io.csv_exporter import CsvExporter    

#NOTE: used in previous versions of the code

# dummy runner = returns every key summarise_run 
class DummyRunner:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, mgr):
        base = {
            'end_step': 10,
            'total_distance': 100.0,
            'sum_decel': 0.0,
            'sudden_brake_count': 0,
            'max_speed': 15.0,
            'max_decel': 0.0,
            'edges_visited': {"a", "b"},
            'tls_encountered': {"tls1"},
            'tls_stop_count': 0,
            'tls_wait_time': 0.0,
            'amber_encountered': 0,
            'red_encountered': 0,
            'amber_run_count': 0,
            'red_run_count': 0,
            'lane_change_count': 0,
            'collision_count': 0,
            'wait_time': 7.0
        }

        # identical dict for both agents
        return {'safe_1': base.copy(), 'risky_1': base.copy()}, 42

@pytest.fixture(autouse=True)
def patch_runner(monkeypatch):
    import src.simulation.batch as sb
    monkeypatch.setattr(sb, "SimulationRunner", DummyRunner)

@pytest.fixture(autouse=True)
def capture_csv(monkeypatch):
    calls = []
    def fake_to_file(self, path, headers, rows):
        calls.append(rows)
    monkeypatch.setattr(CsvExporter, "to_file", fake_to_file)
    return calls

def test_batch_exports_waiting_time(capture_csv):
    main(num_runs=1)
    # per-run and averages
    assert len(capture_csv) == 2
    per_run_rows = capture_csv[0]
    # summarise_run rounds wait time into the last column
    assert any(row[-1] == 7.0 for row in per_run_rows)
