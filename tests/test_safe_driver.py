import pytest

from src.agents.safe_driver import SafeDriver
from src.simulation.tls_recorder import TLSEventRecorder
import src.agents.safe_driver as safe_mod

@pytest.fixture(autouse=True)
def setup_traci(monkeypatch):
    """
    Stub out all TraCI calls SafeDriver.update() may invoke.
    By default:
      - getSpeed() → 5.0 m/s
      - getMaxSpeed() → 15.0 m/s
      - slowDown(...) and setSpeed(...) are no-ops (can be overridden per-test)
    """
    monkeypatch.setattr(safe_mod.traci.vehicle, "getSpeed", lambda vid: 5.0)
    monkeypatch.setattr(safe_mod.traci.vehicle, "getMaxSpeed", lambda vid: 15.0)
    monkeypatch.setattr(safe_mod.traci.vehicle, "slowDown", lambda *args, **kwargs: None)
    monkeypatch.setattr(safe_mod.traci.vehicle, "setSpeed", lambda *args, **kwargs: None)
    return monkeypatch

def test_slow_on_amber(setup_traci):
    recorder = TLSEventRecorder()
    driver = SafeDriver("v1", recorder)

    # Simulate an amber light 10 m ahead
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

    # Amber-first tracking not relevant here; simulate red 5 m ahead
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

    # DECEL_RED = 4.5 → stopping distance ~ (5²)/(2·4.5)=2.78; +0.5 margin=3.28, 
    # and 5.0>3.28 so it should decelerate, not emergency-stop
    assert recorder.red_encounters == 1
    assert driver.state == "stopped"
    assert calls == [("v1", 0.0, SafeDriver.DECEL_RED)]

def test_emergency_stop_on_red(setup_traci):
    recorder = TLSEventRecorder()
    driver = SafeDriver("v1", recorder)

    # Make dist small enough to trigger emergency stop
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

    # Now simulate green
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
    assert calls == [("v1", 15.0)]  # 15.0 is our stubbed getMaxSpeed()

def test_reset_to_approach_after_passing(setup_traci):
    recorder = TLSEventRecorder()
    driver = SafeDriver("v1", recorder)
    driver.state = "passing"

    # Negative dist < -2.0 should reset to 'approach'
    setup_traci.setattr(
        safe_mod.traci.vehicle,
        "getNextTLS",
        lambda vid: [("tls1", 0, -3.0, "gggg")]
    )

    driver.update()
    assert driver.state == "approach"
