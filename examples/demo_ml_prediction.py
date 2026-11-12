#!/usr/bin/env python3
"""
Demonstration Script for Phase 5 ML Failure Prediction.
Streams a real trajectory turn-by-turn through the Signals Engine
and evaluates real-time failure-risk probability using the ML classifier.
"""

import json
import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.predictor import AgentFailurePredictor
from src.signals.engine import RuntimeSignalsEngine

UNSAFE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "aftraj_unsafe.parquet")


def run_demo():
    print("=" * 85)
    print("      DEMONSTRATION: REAL-TIME ML AGENT FAILURE RISK PREDICTION")
    print("=" * 85)

    unsafe_df = pd.read_parquet(UNSAFE_PATH)
    # Select sample trajectory with decisive failure
    sample = None
    for _, row in unsafe_df.iterrows():
        if row["domain"] == "agentic" and row["mistake_step"] >= 2:
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

    print(f"Trajectory ID:       {conv_id}")
    print(f"Domain:              {domain}")
    print(f"Total Turns:         {len(turns)}")
    print(f"Decisive Mistake:    Step {k_star} (Responsible Agent: {mistake_agent})")
    print(f"Task Prompt:         {task[:120]}...\n")

    engine = RuntimeSignalsEngine(task_prompt=task)
    predictor = AgentFailurePredictor()

    print("-" * 85)
    print(f"{'Step':<5} | {'Role':<14} | {'Retries':<7} | {'FailRate':<8} | {'LoopScore':<9} | {'Stagnation':<10} | {'Failure Risk (p)':<18} | {'Status'}")
    print("-" * 85)

    for step_idx, turn in enumerate(turns):
        sig = engine.update(turn)
        risk_p = predictor.predict_risk(sig)

        status = ""
        if step_idx == k_star:
            status = ">> DECISIVE MISTAKE <<"
        elif step_idx > k_star:
            status = "(Post-Mistake)"
        elif risk_p >= 0.50:
            status = "Elevated Risk Warning"
        else:
            status = "Healthy"

        print(
            f"{step_idx:<5} | "
            f"{sig.role[:14]:<14} | "
            f"{sig.active_retry_count:<7} | "
            f"{sig.tool_failure_rate:<8.2f} | "
            f"{sig.loop_indicator_score:<9.2f} | "
            f"{sig.stagnation_score:<10.2f} | "
            f"{risk_p:<18.4f} | "
            f"{status}"
        )

    print("-" * 85)
    print("\nProbability Interpretation Guide:")
    print("  - p in [0.00, 0.30): Low Risk     --> Execution is progressing normally.")
    print("  - p in [0.30, 0.60): Moderate Risk--> Early anomalies; candidate for LLM Judge confirmation.")
    print("  - p in [0.60, 1.00]: High Risk    --> Severe danger of failure; triggers intervention engine.")
    print("=" * 85)


if __name__ == "__main__":
    run_demo()

