import pytest

from src.agents.safe_driver import SafeDriver
from src.simulation.tls_recorder import TLSEventRecorder
import src.agents.safe_driver as safe_mod

@pytest.fixture(autouse=True)
def setup_traci(monkeypatch):

    # stub out traci calls
    monkeypatch.setattr(safe_mod.traci.vehicle, "getSpeed", lambda vid: 5.0)
    monkeypatch.setattr(safe_mod.traci.vehicle, "getMaxSpeed", lambda vid: 15.0)
    monkeypatch.setattr(safe_mod.traci.vehicle, "slowDown", lambda *args, **kwargs: None)
    monkeypatch.setattr(safe_mod.traci.vehicle, "setSpeed", lambda *args, **kwargs: None)
    return monkeypatch

def test_slow_on_amber(setup_traci):
    recorder = TLSEventRecorder()
    driver = SafeDriver("v1", recorder)

    # simulate amber 10m
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "getNextTLS",
        lambda vid: [("tls1", 0, 10.0, "yryr")]
    )

    calls = []
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "slowDown",
        lambda vid, speed, decel: calls.append((vid, speed, decel))
    )

    driver.update()

    assert recorder.amber_encounters == 1
    assert driver.state == "slowing"
    assert calls == [("v1", 0.0, SafeDriver.DECEL_AMBER)]

def test_stop_on_red_decelerate(setup_traci):
    recorder = TLSEventRecorder()
    driver = SafeDriver("v1", recorder)

    # simulate red 5m ahead
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "getNextTLS",
        lambda vid: [("tls1", 0, 5.0, "rrrr")]
    )

    calls = []
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "slowDown",
        lambda vid, speed, decel: calls.append((vid, speed, decel))
    )

    driver.update()

    # shouldn't emergency stop
    assert recorder.red_encounters == 1
    assert driver.state == "stopped"
    assert calls == [("v1", 0.0, SafeDriver.DECEL_RED)]

def test_emergency_stop_on_red(setup_traci):
    recorder = TLSEventRecorder()
    driver = SafeDriver("v1", recorder)

    # trigger emergency stop
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "getNextTLS",
        lambda vid: [("tls1", 0, 1.0, "rrrr")]
    )

    calls = []
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "setSpeed",
        lambda vid, speed: calls.append((vid, speed))
    )

    driver.update()

    assert recorder.red_encounters == 1
    assert driver.state == "stopped"
    assert calls == [("v1", 0.0)]

def test_passing_on_green_after_red(setup_traci):
    recorder = TLSEventRecorder()
    driver = SafeDriver("v1", recorder)
    driver.state = "stopped"

    # simulate green
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "getNextTLS",
        lambda vid: [("tls1", 0, 5.0, "gggg")]
    )

    calls = []
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "setSpeed",
        lambda vid, speed: calls.append((vid, speed))
    )

    driver.update()

    assert driver.state == "passing"
    assert calls == [("v1", 15.0)]

def test_reset_to_approach_after_passing(setup_traci):
    recorder = TLSEventRecorder()
    driver = SafeDriver("v1", recorder)
    driver.state = "passing"

    # negative dist = approach
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "getNextTLS",
        lambda vid: [("tls1", 0, -3.0, "gggg")]
    )

    driver.update()
    assert driver.state == "approach"
