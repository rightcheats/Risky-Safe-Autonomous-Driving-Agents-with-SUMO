# src/simulation/experiment4.py

from pathlib import Path
import random
import statistics as stats
import traci
from traci.exceptions import TraCIException
import csv

# ——————————————————————————————————————————————————————————————
# Configuration
# ——————————————————————————————————————————————————————————————

# Threshold for counting a “sudden brake” (m/s²)
SUDDEN_BRAKE_THRESHOLD = 3.0

# How many valid episodes to run
NUM_EPISODES = 300

# Steps cap per episode just in case
MAX_STEPS_PER_EPISODE = 10_000

# ——————————————————————————————————————————————————————————————
def run_episode(sumo_cfg: str):
    """
    Starts SUMO, picks a random non‐degenerate route (up to 100 tries),
    injects one vehicle, steps until arrival, and returns:
      (journey_time_steps, total_distance, sudden_brake_count, max_decel)
    Raises RuntimeError if no valid route found.
    """
    traci.start([
        "sumo", "-c", sumo_cfg,
        "--start", "--quit-on-end", "--no-step-log"
    ])

    # pick two random edges until findRoute yields >1 edge
    edges = traci.edge.getIDList()
    route_edges = []
    for _ in range(100):
        a, b = random.sample(edges, 2)
        try:
            cand = traci.simulation.findRoute(a, b)
        except TraCIException:
            continue
        if len(cand.edges) > 1:
            start_edge, end_edge = a, b
            route_edges = cand.edges
            break

    if not route_edges:
        traci.close()
        raise RuntimeError("Could not find any non-degenerate route in 100 attempts")

    route_id = f"route_{start_edge}_to_{end_edge}"
    traci.route.add(route_id, route_edges)
    traci.vehicle.add(
        vehID="baseline_1",
        routeID=route_id,
        departSpeed="max",
        departLane="best"
    )
    traci.vehicle.setColor("baseline_1", (0, 0, 255))

    prev_speed = traci.vehicle.getSpeed("baseline_1")
    prev_dist  = 0.0
    sudden_brakes = 0
    max_decel    = 0.0

    for step in range(1, MAX_STEPS_PER_EPISODE + 1):
        traci.simulationStep()
        if "baseline_1" not in traci.vehicle.getIDList():
            journey_time = step
            total_distance = prev_dist
            break

        cs = traci.vehicle.getSpeed("baseline_1")
        cd = traci.vehicle.getDistance("baseline_1")
        decel = max(prev_speed - cs, 0.0)
        if decel > SUDDEN_BRAKE_THRESHOLD:
            sudden_brakes += 1
        max_decel = max(max_decel, decel)

        prev_speed = cs
        prev_dist  = cd
    else:
        journey_time = MAX_STEPS_PER_EPISODE
        total_distance = prev_dist

    traci.close()
    return journey_time, total_distance, sudden_brakes, max_decel

# ——————————————————————————————————————————————————————————————
def main():
    # locate SUMO config
    ROOT     = Path(__file__).resolve().parents[2]
    SUMO_CFG = ROOT / "src" / "osm_data" / "osm.sumocfg"
    if not SUMO_CFG.is_file():
        raise FileNotFoundError(f"SUMO config not found at {SUMO_CFG}")

    results = []
    for episode in range(1, NUM_EPISODES + 1):
        try:
            rt, dist, sb, md = run_episode(str(SUMO_CFG))
        except RuntimeError as e:
            # this should be rare; abort entire experiment if it happens
            print(f"[ERROR] Episode {episode}: {e}")
            break

        results.append((rt, dist, sb, md))
        print(f"[Episode {episode}/{NUM_EPISODES}] "
              f"time={rt} steps, dist={dist:.1f}m, "
              f"brakes={sb}, max_decel={md:.2f}m/s²")

    # compute averages
    times, dists, brakes, decels = zip(*results)
    speeds = [d/t if t > 0 else 0.0 for d, t in zip(dists, times)]
    summary = {
        "AvgJourneyTime(steps)" : round(stats.mean(times), 2),
        "AvgSpeed(m/s)"         : round(stats.mean(speeds),   2),
        "AvgSuddenBrakes"       : round(stats.mean(brakes),   2),
        "AvgMaxDecel(m/s²)"     : round(stats.mean(decels),   2),
    }

    # write two-column CSV
    out_dir = ROOT / "csv_results" / "exp4"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "baseline_summary.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Metric", "Value"])
        for k, v in summary.items():
            w.writerow([k, v])

    print(f"\nExperiment complete – results at {csv_path}")

if __name__ == "__main__":
    main()
