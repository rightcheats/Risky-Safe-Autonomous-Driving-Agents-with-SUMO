import pytest
from src.simulation.simulation_runner import SimulationRunner

# dummy agents, tls recorder stub
class DummyAgent:
    def __init__(self, vid):
        self.vehicle_id = vid
        class R:
            amber_encounters = red_encounters = amber_runs = red_runs = 0
        self.recorder = R()

# dummy agent manager
class DummyManager:
    def __init__(self):
        self.agents = [DummyAgent("safe_1"), DummyAgent("risky_1")]
    def inject_agents(self): pass
    def get_destination_edge(self): return "EDGE_0"
    def get_route_label(self):      return 0
    def update_agents(self, step):  pass

# dummy traci
class DummyTraci:
    def __init__(self):
        self.wait = 5.0
    def vehicle_getWaitingTime(self, _veh_id):
        return self.wait
    def vehicle_getAccumulatedWaitingTime(self, _veh_id):
        return self.wait

@pytest.fixture(autouse=True)
def patch_traci(monkeypatch):

    import src.simulation.simulation_runner as sr

    # stub sumo, no real connection
    monkeypatch.setattr(sr.traci, "start", lambda cmd: None)
    monkeypatch.setattr(sr.traci, "close", lambda: None)

    dummy = DummyTraci()

    monkeypatch.setattr(sr.traci.vehicle, "getWaitingTime",
                        dummy.vehicle_getWaitingTime)
    monkeypatch.setattr(sr.traci.vehicle, "getAccumulatedWaitingTime",
                        dummy.vehicle_getAccumulatedWaitingTime)
    return dummy

@pytest.fixture
def runner(tmp_path):
    # minimal SUMO config
    cfg = tmp_path / "dummy.sumocfg"
    cfg.write_text("""
    <configuration>
      <input>
        <net-file value="foo.net.xml"/>
        <route-files value="foo.rou.xml"/>
      </input>
      <time><end value="1"/></time>
    </configuration>
    """)
    # zero steps = skip loop
    # but still run post-loop logic
    return SimulationRunner(sumo_binary="sumo",
                            sumo_config=str(cfg),
                            max_steps=0)

def test_waiting_time_is_captured(runner):
    mgr = DummyManager()
    data, _ = runner.run(mgr)
    assert data["safe_1"]["wait_time"] == 5.0
    assert data["risky_1"]["wait_time"] == 5.0
