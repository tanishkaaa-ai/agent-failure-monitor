#!/usr/bin/env python3
"""
Demonstration Script for Phase 4 Signals Engine.
Loads an actual trajectory from AFTraj and prints step-by-step runtime signals.
"""

import json
import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.signals.engine import RuntimeSignalsEngine

UNSAFE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "aftraj_unsafe.parquet")


def run_demo():
    print("=" * 80)
    print("      DEMONSTRATION: RUNTIME SIGNALS ENGINE (STEP-BY-STEP AUDITING)")
    print("=" * 80)

    unsafe_df = pd.read_parquet(UNSAFE_PATH)
    # Pick a trajectory with tool calls
    sample = None
    for _, row in unsafe_df.iterrows():
        if row["num_turns"] >= 6 and row["mistake_step"] >= 3:
            sample = row
            break

    if sample is None:
        sample = unsafe_df.iloc[0]

    conv_id = sample["conv_id"]
    domain = sample["domain"]
    task = sample["task"]
    k_star = sample["mistake_step"]
    mistake_agent = sample["mistake_agent"]
    turns = list(sample["turns"])

    print(f"Trajectory ID:      {conv_id}")
    print(f"Domain:             {domain}")
    print(f"Total Turns:        {len(turns)}")
    print(f"Decisive Error Step: Step {k_star} (Mistake Agent: {mistake_agent})")
    print(f"Task Prompt:        {task[:120]}...\n")

    # Initialize live streaming engine
    engine = RuntimeSignalsEngine(task_prompt=task)

    print("-" * 80)
    print(f"{'Step':<5} | {'Role':<14} | {'Retries':<7} | {'FailRate':<8} | {'LoopScore':<9} | {'Stagnation':<10} | {'ActDiversity':<12} | {'RiskScore':<9}")
    print("-" * 80)

    for step_idx, turn in enumerate(turns):
        sig = engine.update(turn)
        status_marker = " [MISTAKE]" if step_idx == k_star else ""

        print(
            f"{step_idx:<5} | "
            f"{sig.role[:14]:<14} | "
            f"{sig.active_retry_count:<7} | "
            f"{sig.tool_failure_rate:<8.2f} | "
            f"{sig.loop_indicator_score:<9.2f} | "
            f"{sig.stagnation_score:<10.2f} | "
            f"{sig.action_diversity:<12.2f} | "
            f"{sig.rule_risk_score:<9.2f}"
            f"{status_marker}"
        )

    print("-" * 80)
    print("\nFeature vector produced for ML model (Step 0):")
    sample_sig = engine.signal_history[0]
    print(json.dumps(sample_sig.to_features_dict(), indent=2))
    print(f"\nTotal numerical features per step: {len(sample_sig.to_numpy())}")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()

