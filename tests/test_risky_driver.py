import pytest
import random
import traci

from src.agents.risky_driver import RiskyDriver
from src.simulation.tls_recorder import TLSEventRecorder

#TODO: update to reflect new stuff

@pytest.fixture(autouse=True)
def stub_traci(monkeypatch):
    calls = {"setSpeed": [], "setAcceleration": [], "setDecel": []}
    # vehicle queries
    monkeypatch.setattr(traci.vehicle, "getSpeed", lambda vid: 5.0)
    monkeypatch.setattr(traci.vehicle, "getMaxSpeed", lambda vid: 15.0)

    # vehicle actions
    monkeypatch.setattr(traci.vehicle, "setSpeed", lambda vid, spd: calls["setSpeed"].append((vid, spd)))
    monkeypatch.setattr(traci.vehicle, "setAcceleration", lambda vid, acc, dur: calls["setAcceleration"].append((vid, acc, dur)))
    monkeypatch.setattr(traci.vehicle, "setDecel", lambda vid, dec: calls["setDecel"].append((vid, dec)))

    # default tls state
    monkeypatch.setattr(traci.trafficlight, "getRedYellowGreenState", lambda tls_id: "gggg")
    return calls

@pytest.fixture(autouse=True)
def stub_random(monkeypatch):
    return monkeypatch


def make_tls(state: str, dist: float):
    """Helper for returning a single traffic-light entry"""
    return [("tls0", 0, dist, state)]


def test_green_cruise(stub_traci):
    rec = TLSEventRecorder()
    d = RiskyDriver("v1", "route", rec)
    pytest.MonkeyPatch().setattr(traci.vehicle, "getNextTLS", lambda v: [])
    d.update()
    assert stub_traci["setSpeed"] == [("v1", 15.0)]
    assert rec.amber_runs == 0 and rec.red_runs == 0


def test_amber_far_runs(stub_traci, stub_random):
    rec = TLSEventRecorder()
    d = RiskyDriver("v1", "route", rec)
    pytest.MonkeyPatch().setattr(traci.vehicle, "getNextTLS", lambda v: make_tls("yryr", 10.0))
    stub_random.setattr(random, "random", lambda: 0.0)
    stub_random.setattr(traci.trafficlight, "getRedYellowGreenState", lambda tls_id: "yryr")
    d.update()
    assert stub_traci["setAcceleration"] == [("v1", d.a_max, d.accel_duration)]
    assert rec.amber_runs == 1


def test_amber_close_gamble_go_and_stop(stub_traci, stub_random):
    rec = TLSEventRecorder()
    d = RiskyDriver("v1", "route", rec)

    # distance triggers gamble branch
    pytest.MonkeyPatch().setattr(traci.vehicle, "getNextTLS", lambda v: make_tls("yryr", 0.5))
    stub_random.setattr(traci.trafficlight, "getRedYellowGreenState", lambda tls_id: "yryr")

    # scenario 1: random < amber_go_prob -> go
    stub_random.setattr(random, "random", lambda: d.amber_go_prob - 0.1)
    d.update()
    assert stub_traci["setSpeed"] == [("v1", 15.0)]
    assert rec.amber_runs == 1
    # reset
    stub_traci["setSpeed"].clear()
    rec.amber_runs = 0

    # scenario 2: random >= amber_go_prob -> stop
    stub_random.setattr(random, "random", lambda: d.amber_go_prob + 0.1)
    d.update()
    assert stub_traci["setDecel"] == [("v1", d.a_c)]
    assert rec.amber_runs == 0

def test_red_fresh_roll_and_brake(stub_traci, stub_random):
    rec = TLSEventRecorder()
    d = RiskyDriver("v1", "route", rec)
    pytest.MonkeyPatch().setattr(traci.vehicle, "getNextTLS", lambda v: make_tls("rrrr", 1.0))
    stub_random.setattr(traci.trafficlight, "getRedYellowGreenState", lambda tls_id: "rrrr")
    d.last_tls_state = "y"
    d.update()
    assert stub_traci["setSpeed"] == [("v1", 15.0)]
    assert rec.red_runs == 1
    # reset
    stub_traci["setSpeed"].clear()
    rec.red_runs = 0
    pytest.MonkeyPatch().setattr(traci.vehicle, "getNextTLS", lambda v: make_tls("rrrr", 5.0))
    d.last_tls_state = "g"
    d.update()
    assert stub_traci["setDecel"] == [("v1", d.a_c)]
    assert rec.red_runs == 0
