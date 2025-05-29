# Risky vs Safe Autonomous Driving Agents with SUMO

## Overview

This project implements and evaluates two Q-learning based autonomous driving agents in SUMO:

- **SafeDriver**: prioritises rule compliance and safety, obeying speed limits and stopping at red/amber lights  
- **RiskyDriver**: prioritises journey efficiency, taking shortcuts, running amber lights, and accepting higher risk  

Core research question:  
> *How do divergent reward functions (“safe” vs. “risky”) in Q-learning-based driving agents alter the trade-off between journey efficiency and traffic-rule compliance, across varied routing scenarios and against a non-learning baseline?*

## Features

- **Tabular Q-learning** with epsilon-greedy policy and per-agent decay schedules  
- **Custom reward functions** encoding safe or risky behaviors  
- **Dynamic route selection** via SUMO’s TraCI API  
- **Metrics collection**: journey time, speed, compliance events (stops/runs), deceleration, collisions, etc.  
- **Batch experiments** with automated CSV export and plots (epsilon-decay, Q-value heatmaps, speed-bin distributions)  

## Requirements

- Python 3.8+  
- [SUMO](https://sumo.dlr.de/) with TraCI and `sumolib`  
- Pip packages: `traci`, `sumolib`, `pytest`, `pandas`, `matplotlib`

Dependencies can be installed via `pip install -r requirements.txt`

*Note: for testing also install `requirements-dev.txt`*

## Configuration

1. SUMO network and route config should be placed under src/simulation/osm_data
2. If needed, update the `SUMO_BINARY` and `SUMO_CONFIG` constants.

## Project Structure



```
project/
├── src/
│   ├── main.py                                 # Entry point
│   ├── agents/
│   │   ├── base_agent.py                       # Abstract agent interface
│   │   ├── safe_driver.py                      # SafeDriver implementation
│   │   ├── risky_driver.py                     # RiskyDriver implementation
│   │   └── learning/
│   │       ├── q_table.py                      # Q-table mechanics & epsilon-greedy
│   │       ├── rewards.py                      # Reward functions
│   │       └── models/                         # Persisted Q-tables
│   │           ├── safe_driver_qtable.pkl      # Saved Q-table for SafeDriver
│   │           └── risky_driver_qtable.pkl     # Saved Q-table for RiskyDriver
│   ├── simulation/
│   │   ├── simulation_runner.py                # SUMO + TraCI loop wrapper
│   │   ├── batch.py                            # Batch orchestration & plotting
│   │   ├── check_edges.py                      # Utility to validate SUMO edges
│   │   └── simulation_setup.py                 # SUMO network & route setup fpr initial testing
│   ├── metrics/
│   │   └── metrics_collector.py                # Aggregates run metrics to CSV
│   └── io/
│       └── csv_exporter.py                     # Writes CSV outputs
├── tests/                                      # All unit tests
│   ├── test_csv_waiting_time.py
│   ├── test_model_creation.py
│   ├── test_q_learning.py
│   ├── test_risky_driver.py
│   ├── test_safe_driver.py
│   ├── test_tls_recorder.py
│   └── test_waiting_time_unit.py
└── README.md

```

## Usage

`python -m src.main -n [num]` will run a batch of simulations `num` times 

Outputs:
- Epsilon decay graph
- Heatmap of Q-values, per agent
- Stacked bar charts showing speed bin distribution, per agent
- CSV of average metrics
- CSV of per-run metrics
- 2x .pkl saved Q-tables
