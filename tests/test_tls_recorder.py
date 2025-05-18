import pytest
from src.simulation.tls_recorder import TLSEventRecorder

@pytest.fixture
def recorder():
    return TLSEventRecorder()

def test_initial_counts_are_zero(recorder):
    assert recorder.amber_encounters == 0
    assert recorder.red_encounters == 0
    assert recorder.amber_runs == 0
    assert recorder.red_runs == 0

def test_saw_methods_increment(recorder):
    recorder.saw_amber()
    recorder.saw_amber()
    recorder.saw_red()
    assert recorder.amber_encounters == 2
    assert recorder.red_encounters == 1

def test_ran_methods_increment(recorder):
    recorder.ran_amber()
    recorder.ran_red()
    recorder.ran_red()
    assert recorder.amber_runs == 1
    assert recorder.red_runs == 2