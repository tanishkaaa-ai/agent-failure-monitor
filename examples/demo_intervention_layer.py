#!/usr/bin/env python3
"""
Demonstration Script for Phase 8 Intervention Layer.
Simulates end-to-end execution monitoring and triggers recovery actions upon ALARM.
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
from src.interventions.engine import InterventionEngine
from src.judge.judge import LLMJudge
from src.judge.llm_client import get_default_llm_client
from src.models.predictor import AgentFailurePredictor
from src.signals.engine import RuntimeSignalsEngine

UNSAFE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "aftraj_unsafe.parquet")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "decision_config.yaml")


def run_demo():
    print("=" * 100)
    print("      END-TO-END DEMO: AGENT MONITORING, DECISION FUSION & INTERVENTION")
    print("=" * 100)

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
    print(f"Task Prompt:         {task[:100]}...\n")

    # Initialize all 5 pipeline layers
    signals_engine = RuntimeSignalsEngine(task_prompt=task)
    ml_predictor = AgentFailurePredictor()
    judge = LLMJudge(client=get_default_llm_client())
    decision_system = DecisionSystem(config=DecisionConfig.from_yaml(CONFIG_PATH))
    intervention_engine = InterventionEngine(max_interventions_per_run=3)

    print("-" * 100)
    print(
        f"{'Step':<5} | {'Role':<12} | {'ML Risk':<8} | {'Judge':<10} | {'Decision':<10} | "
        f"{'Intervention Action':<24} | {'Status'}"
    )
    print("-" * 100)

    interventions_triggered = 0

    for step_idx, turn in enumerate(turns):
        # 1. Signals Engine
        sig = signals_engine.update(turn)

        # 2. ML Classifier
        risk_p = ml_predictor.predict_risk(sig)

        # 3. LLM Judge
        judge_res = judge.judge_step(
            task_prompt=task,
            turns_prefix=signals_engine.history,
            signals=sig,
            ml_risk_prob=risk_p,
        )

        # 4. Decision System
        decision_rec = decision_system.decide(
            signals=sig,
            ml_risk_prob=risk_p,
            judge_response=judge_res,
        )

        # 5. Intervention Layer (activates ONLY on ALARM)
        action_name = "None (Healthy)"
        outcome_status = "N/A"

        if decision_rec.decision == FinalDecision.ALARM:
            outcome = intervention_engine.handle_alarm(
                decision_record=decision_rec,
                signals=sig,
                task_prompt=task,
                trajectory_history=signals_engine.history,
            )
            action_name = outcome.action_type.value
            outcome_status = outcome.status
            interventions_triggered += 1

        marker = " [MISTAKE]" if step_idx == k_star else ""

        print(
            f"{step_idx:<5} | "
            f"{sig.role[:12]:<12} | "
            f"{risk_p:<8.4f} | "
            f"{judge_res.verdict.value:<10} | "
            f"{decision_rec.decision.value:<10} | "
            f"{action_name:<24} | "
            f"{outcome_status}"
            f"{marker}"
        )

    print("-" * 100)
    print(f"\nExecution Complete. Total Interventions Applied: {interventions_triggered}")

    if intervention_engine.intervention_history:
        print("\nSample Corrective Message Injected to Agent:")
        first_intervention = intervention_engine.intervention_history[0]
        print(f"Action:  {first_intervention.action_type.value}")
        print(f"Details: {first_intervention.details}")
        print(f"Message: {first_intervention.injected_message['content']}")

    print("\nIntervention Layer Summary:")
    print(json.dumps(intervention_engine.get_summary(), indent=2))
    print("=" * 100)


if __name__ == "__main__":
    run_demo()

