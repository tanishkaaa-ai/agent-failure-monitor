#!/usr/bin/env python3
"""
Lightweight Real-Time Agent Failure Prediction and Intervention System.
Main runnable entry-point script.

Usage:
  python main.py --demo              # Run live end-to-end demonstration on a sample AFTraj trajectory
  python main.py --eval              # Run evaluation over test split trajectories
  python main.py --interactive       # Interactive step-by-step agent simulation
"""

import argparse
import json
import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipeline import AgentFailureGuardSystem
from src.decision.system import FinalDecision

CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "decision_config.yaml")
UNSAFE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "aftraj_unsafe.parquet")
SAFE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "aftraj_safe.parquet")


def run_demo(trajectory_type: str = "unsafe", index: int = 0):
    print("=" * 105)
    print("  LIGHTWEIGHT REAL-TIME AGENT FAILURE PREDICTION AND INTERVENTION SYSTEM")
    print("=" * 105)

    data_path = UNSAFE_PATH if trajectory_type == "unsafe" else SAFE_PATH
    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at {data_path}. Please complete Phase 2 download first.")
        return

    df = pd.read_parquet(data_path)
    sample = df.iloc[index]

    conv_id = sample["conv_id"]
    domain = sample["domain"]
    task = str(sample["task"])
    turns = list(sample["turns"])
    k_star = sample.get("mistake_step", -1)
    mistake_agent = sample.get("mistake_agent", "none")

    print(f"Trajectory ID:       {conv_id}")
    print(f"Domain:              {domain}")
    print(f"Dataset Split:       {trajectory_type.upper()}")
    print(f"Total Turns:         {len(turns)}")
    if k_star >= 0:
        print(f"Ground-Truth Decisive Error: Turn {k_star} (Mistake Agent: {mistake_agent})")
    else:
        print(f"Ground-Truth: Verified SAFE trajectory (No failure step)")
    print(f"Task Prompt:         {task[:100]}...\n")

    # Initialize complete guard system
    guard = AgentFailureGuardSystem(config_path=CONFIG_PATH)
    guard.start_session(task_prompt=task)

    print("-" * 105)
    print(
        f"{'Step':<5} | {'Role':<12} | {'ML Risk':<8} | {'Judge':<10} | {'Decision':<10} | "
        f"{'Proceed?':<9} | {'Intervention Action':<22} | {'Applied Rule'}"
    )
    print("-" * 105)

    for step_idx, turn in enumerate(turns):
        res = guard.monitor_step(turn)

        act_str = res.intervention.action_type.value if res.intervention else "None (Healthy)"
        proceed_str = "YES" if res.allow_proceed else "HALT"
        marker = " [MISTAKE]" if step_idx == k_star else ""

        print(
            f"{res.step_idx:<5} | "
            f"{res.role[:12]:<12} | "
            f"{res.ml_risk_prob:<8.4f} | "
            f"{res.judge_verdict:<10} | "
            f"{res.decision.value:<10} | "
            f"{proceed_str:<9} | "
            f"{act_str:<22} | "
            f"{res.applied_rule}"
            f"{marker}"
        )

        if not res.allow_proceed:
            print(f"\n>>> [SAFETY SHIFT]: Execution halted at step {res.step_idx} ({res.applied_rule}) <<<")
            break

    print("-" * 105)
    print("\nSession Summary:")
    print(json.dumps(guard.get_summary(), indent=2))

    log_path = os.path.join(PROJECT_ROOT, "audit_log_demo.json")
    guard.export_audit_log(log_path)
    print(f"\nAudit trail exported to: {log_path}")
    print("=" * 105)


def run_eval(num_samples: int = 10):
    print("=" * 80)
    print(f"  RUNNING BATCH EVALUATION OVER {num_samples} TEST TRAJECTORIES")
    print("=" * 80)

    unsafe_df = pd.read_parquet(UNSAFE_PATH)
    guard = AgentFailureGuardSystem(config_path=CONFIG_PATH)

    results = []
    for i in range(min(num_samples, len(unsafe_df))):
        sample = unsafe_df.iloc[i]
        summary = guard.run_trajectory(
            task_prompt=str(sample["task"]),
            turns=list(sample["turns"]),
        )
        results.append({
            "conv_id": sample["conv_id"],
            "domain": sample["domain"],
            "mistake_step": sample["mistake_step"],
            "monitored_steps": summary["total_monitored_steps"],
            "alarms": summary["total_alarms"],
            "interventions": summary["total_interventions"],
            "terminated": summary["is_terminated"],
        })

    eval_df = pd.DataFrame(results)
    print(eval_df.to_string(index=False))
    print("-" * 80)
    print(f"Average alarms per run:        {eval_df['alarms'].mean():.2f}")
    print(f"Average interventions per run: {eval_df['interventions'].mean():.2f}")
    print(f"Percentage halted/terminated:  {eval_df['terminated'].mean()*100:.1f}%")
    print("=" * 80)


def run_interactive():
    print("=" * 70)
    print("       INTERACTIVE AGENT FAILURE MONITOR & INTERCEPTOR")
    print("=" * 70)
    task = input("\nEnter Agent Task Prompt (or press Enter for default): ").strip()
    if not task:
        task = "Analyze quarterly revenue from sales_db and generate report."

    guard = AgentFailureGuardSystem(config_path=CONFIG_PATH)
    guard.start_session(task_prompt=task)
    print(f"\nSession started for task: '{task}'")
    print("Enter agent turns interactively. Type 'exit' to quit.\n")

    step = 0
    while True:
        print(f"\n--- Turn {step} Input ---")
        role = input("Role (e.g. CodeWriter, MathSolver, environment) [assistant]: ").strip() or "assistant"
        if role.lower() == "exit":
            break
        thought = input("Thought (reasoning) []: ").strip()
        action = input("Action (e.g. [{\"name\": \"db_query\", \"arguments\": \"...\"}]) []: ").strip()
        content = input("Content (message/output) []: ").strip()

        turn = {"role": role, "thought": thought, "action": action, "content": content}
        res = guard.monitor_step(turn)

        print("\n[GUARD REPORT]:")
        print(f"  - Decision:     {res.decision.value} (Rule: {res.applied_rule})")
        print(f"  - ML Failure p: {res.ml_risk_prob:.4f}")
        print(f"  - Judge:        {res.judge_verdict} ({res.judge_category}, conf={res.judge_confidence:.2f})")
        print(f"  - Proceed?:     {'YES' if res.allow_proceed else 'NO (HALTED)'}")

        if res.intervention:
            print(f"  - INTERVENTION: {res.intervention.action_type.value} ({res.intervention.status})")
            print(f"    Message:      {res.intervention.injected_message['content']}")

        if not res.allow_proceed:
            print("\nExecution terminated by guard. Session ended.")
            break
        step += 1


def main():
    parser = argparse.ArgumentParser(
        description="Lightweight Real-Time Agent Failure Prediction and Intervention System"
    )
    parser.add_argument("--demo", action="store_true", help="Run demonstration on sample trajectory")
    parser.add_argument("--safe", action="store_true", help="Use safe trajectory for demo")
    parser.add_argument("--eval", action="store_true", help="Run batch evaluation over test trajectories")
    parser.add_argument("--interactive", action="store_true", help="Start interactive step-by-step CLI")
    parser.add_argument("--index", type=int, default=0, help="Trajectory index for demo (default: 0)")

    args = parser.parse_args()

    if args.interactive:
        run_interactive()
    elif args.eval:
        run_eval()
    else:
        # Default to demo
        traj_type = "safe" if args.safe else "unsafe"
        run_demo(trajectory_type=traj_type, index=args.index)


if __name__ == "__main__":
    main()

