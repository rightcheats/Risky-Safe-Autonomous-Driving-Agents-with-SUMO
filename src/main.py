"""
Entry-point to run the batch simulation
"""

import argparse
from src.simulation.batch import main as run_batch

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the SUMO batch simulation for safe vs. risky drivers."
    )
    parser.add_argument(
        "-n", "--num-runs",
        type=int,
        default=100,
        help="Number of simulation runs (default: 100)"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    run_batch(args.num_runs)

if __name__ == "__main__":
    main()
