"""
LLM Intervention Planner for Ambiguous/UNKNOWN Failure Scenarios.
Invoked when reason category is UNKNOWN to recommend a targeted recovery action.
Validates recommended actions and tools before acceptance.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.interventions.actions import InterventionActionType, InterventionPlan
from src.interventions.registry import ToolRegistry
from src.judge.llm_client import BaseLLMClient, get_default_llm_client

logger = logging.getLogger("intervention_planner")

PLANNER_SYSTEM_PROMPT = """You are an expert AI Agent Recovery and Intervention Planner.
The execution auditor has raised an ALARM with category UNKNOWN, indicating an ambiguous or complex anomaly.
Your task is to analyze the situation and recommend exactly ONE recovery action from the following list:
- RETRY_WITH_BACKOFF: If the failure appears transient and can be resolved by retrying.
- SWITCH_TOOL: If a specific tool is broken and an alternative should be tried.
- BREAK_LOOP_AND_REPLAN: If the agent is stuck in an implicit loop.
- REPLAN: If the agent's strategy or task alignment needs a course correction.
- ESCALATE_TO_HUMAN: If the situation is high-risk, ambiguous, or irreversible.
- TERMINATE: If the task is impossible, broken beyond recovery, or budget is exhausted.

Return a valid JSON object with these keys:
{
  "action_type": "RETRY_WITH_BACKOFF" | "SWITCH_TOOL" | "BREAK_LOOP_AND_REPLAN" | "REPLAN" | "ESCALATE_TO_HUMAN" | "TERMINATE",
  "target_tool": "name_of_tool_or_null",
  "prompt_injection": "Concise instruction to guide the agent",
  "rationale": "1-2 sentence justification"
}
Do NOT include markdown formatting outside the JSON.
"""


class LLMInterventionPlanner:
    """Prompted LLM planner for resolving UNKNOWN or complex alarms."""

    def __init__(self, registry: ToolRegistry, client: Optional[BaseLLMClient] = None):
        self.registry = registry
        self.client = client or get_default_llm_client()

    def plan_intervention(
        self,
        task_prompt: str,
        recent_turns: List[Dict[str, Any]],
        ml_risk_prob: float,
        rationale: str,
    ) -> InterventionPlan:
        """
        Request LLM intervention plan and validate output against registry.
        """
        user_prompt = f"""### INTERVENTION PLANNING REQUEST
Task: "{task_prompt}"
Decision Alarm Rationale: {rationale}
ML Failure Risk Probability: {ml_risk_prob:.2f}
Recent Turns Count: {len(recent_turns)}

Registered Tools: {self.registry.list_tools()}

Recommend the most appropriate single recovery action.
"""
        try:
            raw_text = self.client.generate(PLANNER_SYSTEM_PROMPT, user_prompt)
            # Clean markdown
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
            clean_text = match.group(1).strip() if match else raw_text.strip()
            data = json.loads(clean_text)

            action_str = data.get("action_type", "").upper()
            action_type = InterventionActionType(action_str)
            target_tool = data.get("target_tool")
            prompt_injection = data.get("prompt_injection")
            plan_rationale = data.get("rationale", "LLM-recommended recovery plan.")

            # Validate tool if SWITCH_TOOL is requested
            fallback_tool = None
            if action_type == InterventionActionType.SWITCH_TOOL:
                if target_tool and self.registry.has_tool(target_tool):
                    fallback_tool = self.registry.get_fallback(target_tool)
                    if not fallback_tool:
                        # Fallback tool not registered; downgrade to ESCALATE_TO_HUMAN
                        action_type = InterventionActionType.ESCALATE_TO_HUMAN
                        plan_rationale += f" (Switch tool requested for '{target_tool}', but no fallback is registered)."
                else:
                    action_type = InterventionActionType.REPLAN
                    plan_rationale += " (Target tool unknown; defaulting to REPLAN)."

            return InterventionPlan(
                action_type=action_type,
                target_tool=target_tool,
                fallback_tool=fallback_tool,
                prompt_injection=prompt_injection,
                rationale=plan_rationale,
            )

        except Exception as e:
            logger.warning(f"Intervention planner failed: {e}. Defaulting to ESCALATE_TO_HUMAN.")
            return InterventionPlan(
                action_type=InterventionActionType.ESCALATE_TO_HUMAN,
                rationale=f"Planner fallback due to: {type(e).__name__}",
                prompt_injection="System paused. Requesting human supervisor review.",
            )

