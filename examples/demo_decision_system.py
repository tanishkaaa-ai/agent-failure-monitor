#!/usr/bin/env python3
"""
Demonstration Script for Phase 7 Decision System.
Connects Signals Engine, ML Predictor, LLM Judge, and Decision System
to produce a final CONTINUE or ALARM verdict at each unfolding step.
"""

import json
import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.decision.config import DecisionConfig
from src.decision.system import DecisionSystem, FinalDecision
from src.judge.judge import LLMJudge
from src.judge.llm_client import get_default_llm_client
from src.models.predictor import AgentFailurePredictor
from src.signals.engine import RuntimeSignalsEngine

UNSAFE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "aftraj_unsafe.parquet")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "decision_config.yaml")


def run_demo():
    print("=" * 95)
    print("        DEMONSTRATION: PHASE 7 MULTI-SIGNAL DECISION-FUSION SYSTEM")
    print("=" * 95)

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
    print(f"Decisive Mistake:    Step {k_star} (Responsible Agent: {mistake_agent})")
    print(f"Task Prompt:         {task[:100]}...\n")

    # Initialize all 4 pipeline components
    engine = RuntimeSignalsEngine(task_prompt=task)
    predictor = AgentFailurePredictor()
    judge = LLMJudge(client=get_default_llm_client())
    config = DecisionConfig.from_yaml(CONFIG_PATH)
    decision_system = DecisionSystem(config=config)

    print("-" * 95)
    print(
        f"{'Step':<5} | {'Role':<12} | {'ML Prob':<8} | {'Judge':<10} | {'Judge Cat':<14} | "
        f"{'FINAL DECISION':<15} | {'Applied Rule'}"
    )
    print("-" * 95)

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

        # 4. Decision Fusion
        record = decision_system.decide(
            signals=sig,
            ml_risk_prob=ml_risk_p,
            judge_response=judge_res,
        )

        marker = " [MISTAKE]" if step_idx == k_star else ""

        print(
            f"{step_idx:<5} | "
            f"{sig.role[:12]:<12} | "
            f"{ml_risk_p:<8.4f} | "
            f"{judge_res.verdict.value:<10} | "
            f"{judge_res.reason_category.value[:14]:<14} | "
            f"{record.decision.value:<15} | "
            f"{record.applied_rule}"
            f"{marker}"
        )

    print("-" * 95)
    print("\nSession Summary:")
    print(json.dumps(decision_system.get_summary(), indent=2))

    print("\nSample Audit Record (Step 10):")
    sample_rec = decision_system.decision_history[min(10, len(decision_system.decision_history) - 1)]
    print(json.dumps(sample_rec.to_dict(), indent=2))
    print("=" * 95)


if __name__ == "__main__":
    run_demo()

