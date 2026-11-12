#!/usr/bin/env python3
"""
Phase 11: Flight Booking Case Study & End-to-End System Demonstration.

Scenario:
  A user asks an agent to find and book a flight from Hyderabad (HYD) to Delhi (DEL)
  under ₹6,000 for tomorrow.

Demonstrates:
  1. Normal agent execution.
  2. A real-world tool failure (Gateway 503 timeout).
  3. Runtime signals extraction (isolated failure suppression).
  4. ML failure-risk probability estimation.
  5. LLM Judge structured diagnostic verdict.
  6. Deterministic Decision System fusion output.
  7. An ALARM trigger when retry threshold is breached.
  8. Intervention Layer activation: SWITCH_TOOL to registered fallback.
  9. Successful agent recovery using alternative tool.
 10. Completed final booking result.
"""

import json
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.decision.config import DecisionConfig
from src.decision.system import FinalDecision
from src.interventions.registry import ToolRegistry
from src.pipeline import AgentFailureGuardSystem

CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "decision_config.yaml")


def create_flight_tool_registry() -> ToolRegistry:
    """Register flight-specific tools and their authorized fallbacks."""
    registry = ToolRegistry()
    # Explicitly register primary flight search tool with verified fallback
    registry.register(
        name="flight_search_api",
        fallback="aggregator_flight_api",
        description="Direct airline partner flight search API."
    )
    registry.register(
        name="aggregator_flight_api",
        fallback=None,
        description="Secondary multi-GDS aggregator flight search API."
    )
    registry.register(
        name="payment_gateway",
        fallback=None,  # No automated fallback for financial transactions
        description="Payment processing gateway."
    )
    return registry


def run_flight_booking_demo():
    print("=" * 115)
    print("        LIGHTWEIGHT REAL-TIME AGENT FAILURE PREDICTION & INTERVENTION SYSTEM")
    print("        CASE STUDY DEMONSTRATION: AUTONOMOUS FLIGHT-BOOKING WORKFLOW")
    print("=" * 115)

    task_prompt = "Find and book a flight from Hyderabad (HYD) to Delhi (DEL) under INR 6,000 for tomorrow."
    print(f"\n[USER GOAL]: \"{task_prompt}\"")
    print("NOTE: Execution actions are simulated agent turns passed through the real, fully-operational guard pipeline.\n")

    registry = create_flight_tool_registry()
    guard = AgentFailureGuardSystem(
        config_path=CONFIG_PATH,
        tool_registry=registry,
        max_interventions=3,
    )
    guard.start_session(task_prompt=task_prompt)

    # Simulated step-by-step agent trajectory
    simulated_turns = [
        # Turn 0: User query
        {
            "role": "user",
            "thought": "",
            "action": "",
            "content": task_prompt,
            "meta_label": "User Query"
        },
        # Turn 1: Agent calls primary flight search tool
        {
            "role": "FlightAgent",
            "thought": "I need to check available flights from HYD to DEL tomorrow within the 6,000 INR budget.",
            "action": '[{"name": "flight_search_api", "arguments": "{\\"origin\\": \\"HYD\\", \\"destination\\": \\"DEL\\", \\"date\\": \\"tomorrow\\", \\"max_price\\": 6000}"}]',
            "content": "",
            "meta_label": "Normal Agent Action (Call Primary API)"
        },
        # Turn 2: Environment returns a 503 error (First failure)
        {
            "role": "environment",
            "thought": "",
            "action": "",
            "content": '{"status": 503, "error": "Service Unavailable: Direct Airline Gateway Timeout"}',
            "meta_label": "Environment Response: First Tool Failure"
        },
        # Turn 3: Agent naively retries the identical failing tool
        {
            "role": "FlightAgent",
            "thought": "The gateway timed out. I will attempt to re-query the same flight search API.",
            "action": '[{"name": "flight_search_api", "arguments": "{\\"origin\\": \\"HYD\\", \\"destination\\": \\"DEL\\", \\"date\\": \\"tomorrow\\", \\"max_price\\": 6000}"}]',
            "content": "",
            "meta_label": "Agent Action: Retry 1 on Failing API"
        },
        # Turn 4: Environment returns another failure
        {
            "role": "environment",
            "thought": "",
            "action": "",
            "content": '{"status": 503, "error": "Service Unavailable: Gateway Still Down"}',
            "meta_label": "Environment Response: Second Tool Failure"
        },
        # Turn 5: Agent attempts a second retry (runaway loop pattern)
        {
            "role": "FlightAgent",
            "thought": "Still failing. Let me try querying flight_search_api again.",
            "action": '[{"name": "flight_search_api", "arguments": "{\\"origin\\": \\"HYD\\", \\"destination\\": \\"DEL\\", \\"date\\": \\"tomorrow\\", \\"max_price\\": 6000}"}]',
            "content": "",
            "meta_label": "Agent Action: Retry 2 (Loop Trigger)"
        },
        # Turn 6: Agent recovers by executing intervention directive (Switch to aggregator_flight_api)
        {
            "role": "FlightAgent",
            "thought": "Intervention received: switching from broken 'flight_search_api' to registered fallback 'aggregator_flight_api'.",
            "action": '[{"name": "aggregator_flight_api", "arguments": "{\\"origin\\": \\"HYD\\", \\"destination\\": \\"DEL\\", \\"max_price\\": 6000}"}]',
            "content": "",
            "meta_label": "Agent Recovery Action: Use Registered Fallback API"
        },
        # Turn 7: Environment returns successful flight data
        {
            "role": "environment",
            "thought": "",
            "action": "",
            "content": '{"flights": [{"flight_no": "6E-204", "airline": "IndiGo", "departure": "08:15", "arrival": "10:30", "price_inr": 4850, "status": "AVAILABLE"}]}',
            "meta_label": "Environment Response: Success"
        },
        # Turn 8: Final agent confirmation and booking
        {
            "role": "FlightAgent",
            "thought": "Flight found within budget (IndiGo 6E-204 at INR 4,850). Presenting confirmation to user.",
            "action": "",
            "content": "Found flight IndiGo 6E-204 (HYD -> DEL, 08:15 AM) for ₹4,850 (under your ₹6,000 budget). Ready to confirm booking!",
            "meta_label": "Final Successful Task Completion"
        }
    ]

    print("-" * 115)
    print(
        f"{'Step':<5} | {'Role':<12} | {'ML Prob':<8} | {'Judge':<10} | {'Decision':<10} | "
        f"{'Proceed?':<9} | {'Intervention Action':<24} | {'Applied Rule'}"
    )
    print("-" * 115)

    for step_idx, turn_data in enumerate(simulated_turns):
        label = turn_data.pop("meta_label", "")
        res = guard.monitor_step(turn_data)

        act_str = res.intervention.action_type.value if res.intervention else "None (Healthy)"
        proceed_str = "YES" if res.allow_proceed else "HALT"

        print(
            f"{res.step_idx:<5} | "
            f"{res.role[:12]:<12} | "
            f"{res.ml_risk_prob:<8.4f} | "
            f"{res.judge_verdict:<10} | "
            f"{res.decision.value:<10} | "
            f"{proceed_str:<9} | "
            f"{act_str:<24} | "
            f"{res.applied_rule}"
        )

        # Highlight key lifecycle events
        if res.decision == FinalDecision.ALARM and res.intervention:
            print(f"      >>> [INTERVENTION FIRED]: {res.intervention.details}")
            print(f"      >>> [INJECTED DIRECTIVE]: {res.intervention.injected_message['content']}")

        if not res.allow_proceed:
            print(f"\n>>> [SAFETY SHIFT]: Execution halted at step {res.step_idx} ({res.applied_rule}) <<<")
            break

    print("-" * 115)
    print("\n" + "=" * 80)
    print("                    FINAL DEMONSTRATION SUMMARY")
    print("=" * 80)
    summary = guard.get_summary()
    print(f"Total Steps Monitored:         {summary['total_monitored_steps']}")
    print(f"Total Alarms Raised:           {summary['total_alarms']}")
    print(f"Total Interventions Executed:  {summary['total_interventions']}")
    print(f"Workflow Final Status:         {'SUCCESS (Recovered)' if not summary['is_terminated'] else 'HALTED'}")
    print(f"Interventions Breakdown:       {json.dumps(summary['intervention_breakdown'])}")
    print("=" * 80)


if __name__ == "__main__":
    run_flight_booking_demo()

