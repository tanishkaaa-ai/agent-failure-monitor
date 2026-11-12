#!/usr/bin/env python3
"""
Demonstration Script for Phase 6 LLM Judge Integration.
Simulates real-time agent auditing by feeding partial trajectory steps,
runtime signals, and ML failure risk into the LLM Judge.
"""

import json
import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.judge.judge import LLMJudge
from src.judge.llm_client import get_default_llm_client
from src.models.predictor import AgentFailurePredictor
from src.signals.engine import RuntimeSignalsEngine

UNSAFE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "aftraj_unsafe.parquet")


def run_demo():
    print("=" * 85)
    print("      DEMONSTRATION: PHASE 6 LLM JUDGE TRAJECTORY AUDITING")
    print("=" * 85)

    unsafe_df = pd.read_parquet(UNSAFE_PATH)
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
    print(f"Decisive Error Step: Step {k_star} (Mistake Agent: {mistake_agent})")
    print(f"Task Prompt:         {task[:120]}...\n")

    # Initialize all three components
    engine = RuntimeSignalsEngine(task_prompt=task)
    predictor = AgentFailurePredictor()
    judge = LLMJudge(client=get_default_llm_client())

    print("-" * 85)
    print(f"{'Step':<5} | {'Role':<12} | {'ML Risk':<8} | {'Judge Verdict':<14} | {'Category':<16} | {'Confidence':<10}")
    print("-" * 85)

    for step_idx, turn in enumerate(turns):
        # 1. Signals Engine
        sig = engine.update(turn)

        # 2. ML Failure Risk Predictor
        ml_risk_p = predictor.predict_risk(sig)

        # 3. LLM Judge Auditing
        judge_res = judge.judge_step(
            task_prompt=task,
            turns_prefix=engine.history,
            signals=sig,
            ml_risk_prob=ml_risk_p,
        )

        status_tag = " [MISTAKE]" if step_idx == k_star else ""

        print(
            f"{step_idx:<5} | "
            f"{sig.role[:12]:<12} | "
            f"{ml_risk_p:<8.4f} | "
            f"{judge_res.verdict.value:<14} | "
            f"{judge_res.reason_category.value:<16} | "
            f"{judge_res.confidence:<10.2f}"
            f"{status_tag}"
        )

    print("-" * 85)
    print("\nDetailed Judge Response at Final Turn:")
    print(json.dumps(judge_res.model_dump(exclude={"raw_response"}), indent=2))
    print("=" * 85)


if __name__ == "__main__":
    run_demo()

