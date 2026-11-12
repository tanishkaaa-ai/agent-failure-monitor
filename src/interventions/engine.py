"""
Phase 8: Intervention Engine
Executes targeted recovery actions when the Decision System triggers an ALARM.
Enforces single-action selection, retry budgets, tool validation, and audit recording.
"""

import logging
from typing import Any, Dict, List, Optional

from src.decision.system import DecisionRecord, FinalDecision
from src.interventions.actions import (
    InterventionActionType,
    InterventionOutcome,
    InterventionPlan,
)
from src.interventions.planner import LLMInterventionPlanner
from src.interventions.registry import ToolRegistry
from src.signals.engine import SignalVector

logger = logging.getLogger("intervention_engine")


class InterventionEngine:
    """
    Intervention Engine responsible for selecting, validating, and applying
    corrective actions when an ALARM is raised.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        max_interventions_per_run: int = 4,
        max_retries_per_tool: int = 2,
        planner: Optional[LLMInterventionPlanner] = None,
    ):
        self.registry = registry or ToolRegistry()
        self.max_interventions_per_run = max_interventions_per_run
        self.max_retries_per_tool = max_retries_per_tool
        self.planner = planner or LLMInterventionPlanner(registry=self.registry)

        self.intervention_history: List[InterventionOutcome] = []
        self.active_tool_retries: Dict[str, int] = {}

    def handle_alarm(
        self,
        decision_record: DecisionRecord,
        signals: SignalVector,
        task_prompt: str,
        trajectory_history: Optional[List[Dict[str, Any]]] = None,
    ) -> InterventionOutcome:
        """
        Select and execute a single appropriate recovery action for an ALARM.
        Activates ONLY when decision == ALARM.
        """
        if decision_record.decision != FinalDecision.ALARM:
            raise ValueError(
                f"InterventionEngine only activates on ALARM. Got: {decision_record.decision}"
            )

        step_idx = decision_record.step_idx
        category = decision_record.judge_category.upper()
        history = trajectory_history or []

        # -------------------------------------------------------------
        # 1. Budget & Exhaustion Guards (Repeated failures -> STOP)
        # -------------------------------------------------------------
        if len(self.intervention_history) >= self.max_interventions_per_run:
            return self._record_outcome(
                step_idx=step_idx,
                category=category,
                action_type=InterventionActionType.TERMINATE,
                status="TERMINATED",
                details=(
                    f"Exhausted total intervention budget ({len(self.intervention_history)} >= "
                    f"{self.max_interventions_per_run}). Terminating run to prevent cost/damage."
                ),
                system_message="[SYSTEM]: Run terminated. Maximum automated recovery attempts exceeded.",
            )

        # -------------------------------------------------------------
        # 2. Critical High-Risk / Extreme Uncertainty -> Human Escalation
        # -------------------------------------------------------------
        if decision_record.ml_risk_prob >= 0.90 and decision_record.judge_confidence >= 0.85:
            return self._record_outcome(
                step_idx=step_idx,
                category=category,
                action_type=InterventionActionType.ESCALATE_TO_HUMAN,
                status="ESCALATED",
                details=(
                    f"Extreme failure risk detected (ML p={decision_record.ml_risk_prob:.2f}, "
                    f"Judge Conf={decision_record.judge_confidence:.2f}). Pausing for human escalation."
                ),
                system_message="[SYSTEM]: Execution paused. High-risk irreversible failure state detected.",
            )

        # -------------------------------------------------------------
        # 3. Category-Specific Action Mapping
        # -------------------------------------------------------------
        # Case A: TEMPORARY_TIMEOUT -> Retry with backoff
        if category == "TEMPORARY_TIMEOUT":
            tool_name = self._identify_target_tool(history, signals)
            retries = self.active_tool_retries.get(tool_name, 0)

            if retries < self.max_retries_per_tool:
                self.active_tool_retries[tool_name] = retries + 1
                backoff_sec = 2.0 ** retries
                return self._record_outcome(
                    step_idx=step_idx,
                    category=category,
                    action_type=InterventionActionType.RETRY_WITH_BACKOFF,
                    status="APPLIED",
                    details=f"Transient timeout on '{tool_name}'. Retrying with {backoff_sec:.1f}s backoff.",
                    system_message=(
                        f"[SYSTEM]: Tool '{tool_name}' timed out. Wait {backoff_sec:.1f}s and retry with "
                        "extended timeout parameters."
                    ),
                    metadata={"target_tool": tool_name, "backoff_seconds": backoff_sec},
                )
            else:
                return self._record_outcome(
                    step_idx=step_idx,
                    category=category,
                    action_type=InterventionActionType.TERMINATE,
                    status="TERMINATED",
                    details=f"Tool '{tool_name}' exhausted retry budget ({retries} retries). Stopping execution.",
                    system_message=f"[SYSTEM]: Tool '{tool_name}' failed repeatedly. Terminating task.",
                )

        # Case B: TOOL_FAILURE -> Switch to registered alternative tool if available
        elif category == "TOOL_FAILURE":
            tool_name = self._identify_target_tool(history, signals)
            fallback_tool = self.registry.get_fallback(tool_name) if tool_name else None

            if fallback_tool:
                return self._record_outcome(
                    step_idx=step_idx,
                    category=category,
                    action_type=InterventionActionType.SWITCH_TOOL,
                    status="APPLIED",
                    details=f"Tool '{tool_name}' failed. Switched to registered fallback '{fallback_tool}'.",
                    system_message=(
                        f"[SYSTEM]: Tool '{tool_name}' encountered an unrecoverable failure. "
                        f"Please use registered alternative tool '{fallback_tool}' to complete the step."
                    ),
                    metadata={"target_tool": tool_name, "fallback_tool": fallback_tool},
                )
            else:
                # Strictly enforce requirement: Do not assume alternative tool exists unless registered!
                return self._record_outcome(
                    step_idx=step_idx,
                    category=category,
                    action_type=InterventionActionType.ESCALATE_TO_HUMAN,
                    status="ESCALATED",
                    details=(
                        f"Tool '{tool_name}' failed, but NO alternative tool is registered in ToolRegistry. "
                        "Escalating to human supervisor."
                    ),
                    system_message=(
                        f"[SYSTEM]: Tool '{tool_name}' failed with no registered fallback. Awaiting human intervention."
                    ),
                )

        # Case C: LOOP -> Break repeated action pattern and replan
        elif category == "LOOP":
            return self._record_outcome(
                step_idx=step_idx,
                category=category,
                action_type=InterventionActionType.BREAK_LOOP_AND_REPLAN,
                status="APPLIED",
                details="Repetitive loop detected. Injected loop-breaking constraint.",
                system_message=(
                    "[SYSTEM]: LOOP WARNING: You are repeating identical actions or thoughts without progress. "
                    "You are forbidden from repeating your previous action. Formulate a different approach immediately."
                ),
            )

        # Case D: PLAN_MISMATCH -> Replan and re-anchor to task objective
        elif category == "PLAN_MISMATCH":
            return self._record_outcome(
                step_idx=step_idx,
                category=category,
                action_type=InterventionActionType.REPLAN,
                status="APPLIED",
                details="Plan mismatch detected. Re-anchored agent to original user task.",
                system_message=(
                    f"[SYSTEM]: PLAN DEVIATION: Your current direction is deviating from the goal. "
                    f"Re-anchor to the objective: \"{task_prompt}\". State your revised plan before taking another action."
                ),
            )

        # Case E: STAGNATION -> Replan or request guidance
        elif category == "STAGNATION":
            if signals.stagnation_score >= 0.80:
                return self._record_outcome(
                    step_idx=step_idx,
                    category=category,
                    action_type=InterventionActionType.ESCALATE_TO_HUMAN,
                    status="ESCALATED",
                    details="Severe stagnation. Requesting human supervisor guidance.",
                    system_message="[SYSTEM]: Execution stagnated across multiple turns without progress. Human assistance required.",
                )
            else:
                return self._record_outcome(
                    step_idx=step_idx,
                    category=category,
                    action_type=InterventionActionType.REPLAN,
                    status="APPLIED",
                    details="Mild stagnation. Injected progress directive.",
                    system_message=(
                        "[SYSTEM]: STAGNATION DETECTED: No substantive progress made. "
                        "Produce a concrete intermediate output or tool invocation now."
                    ),
                )

        # Case F: UNKNOWN / Other -> Use dedicated LLM Intervention Planner
        else:
            plan = self.planner.plan_intervention(
                task_prompt=task_prompt,
                recent_turns=history[-5:] if history else [],
                ml_risk_prob=decision_record.ml_risk_prob,
                rationale=decision_record.rationale,
            )
            status = "APPLIED"
            if plan.action_type == InterventionActionType.ESCALATE_TO_HUMAN:
                status = "ESCALATED"
            elif plan.action_type == InterventionActionType.TERMINATE:
                status = "TERMINATED"

            return self._record_outcome(
                step_idx=step_idx,
                category=category,
                action_type=plan.action_type,
                status=status,
                details=f"LLM Planner recommended {plan.action_type.value}: {plan.rationale}",
                system_message=f"[SYSTEM]: {plan.prompt_injection or plan.rationale}",
                metadata=plan.metadata,
            )

    def _identify_target_tool(self, history: List[Dict[str, Any]], signals: SignalVector) -> str:
        """Find the name of the failing or active tool from history."""
        # Check last actions in history
        for turn in reversed(history):
            action = str(turn.get("action", "") or "")
            if action:
                from src.signals.engine import parse_tools_from_action
                tools = parse_tools_from_action(action)
                if tools:
                    return tools[0][0]
        return "generic_tool"

    def _record_outcome(
        self,
        step_idx: int,
        category: str,
        action_type: InterventionActionType,
        status: str,
        details: str,
        system_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InterventionOutcome:
        injected = {
            "role": "system",
            "thought": "",
            "action": "",
            "content": system_message,
        }
        outcome = InterventionOutcome(
            step_idx=step_idx,
            decision_reason_category=category,
            action_type=action_type,
            status=status,
            details=details,
            injected_message=injected,
            metadata=metadata or {},
        )
        self.intervention_history.append(outcome)
        logger.info(
            f"[Step {step_idx}] INTERVENTION: {action_type.value} ({status}) | Details: {details}"
        )
        return outcome

    def reset(self) -> None:
        """Reset internal intervention tracking."""
        self.intervention_history.clear()
        self.active_tool_retries.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Summary of interventions performed in session."""
        total = len(self.intervention_history)
        actions = {}
        for out in self.intervention_history:
            a_val = out.action_type.value
            actions[a_val] = actions.get(a_val, 0) + 1

        return {
            "total_interventions": total,
            "actions_executed": actions,
        }

