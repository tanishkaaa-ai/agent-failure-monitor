"""
Phase 9: Complete System Pipeline & Runtime Agent Guard.
Unifies Signals Engine, ML Predictor, LLM Judge, Decision System,
and Intervention Layer into an end-to-end real-time guardian.
"""

from dataclasses import asdict, dataclass
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

from src.decision.config import DecisionConfig
from src.decision.system import DecisionRecord, DecisionSystem, FinalDecision
from src.interventions.actions import InterventionActionType, InterventionOutcome
from src.interventions.engine import InterventionEngine
from src.interventions.registry import ToolRegistry
from src.judge.judge import LLMJudge
from src.judge.schema import JudgeResponse
from src.models.predictor import AgentFailurePredictor
from src.signals.engine import RuntimeSignalsEngine, SignalVector

logger = logging.getLogger("agent_guard")


@dataclass
class GuardStepResult:
    """Unified result of monitoring a single agent step."""
    step_idx: int
    role: str
    decision: FinalDecision
    allow_proceed: bool
    ml_risk_prob: float
    judge_verdict: str
    judge_category: str
    judge_confidence: float
    applied_rule: str
    decision_rationale: str
    intervention: Optional[InterventionOutcome] = None
    injected_feedback: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value
        if self.intervention:
            d["intervention"] = self.intervention.to_dict()
        return d


class AgentFailureGuardSystem:
    """
    Complete Integrated Application for Real-Time Agent Failure Prediction
    and Intervention.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        max_interventions: int = 4,
    ):
        # 1. Configuration
        if config_path and os.path.exists(config_path):
            self.config = DecisionConfig.from_yaml(config_path)
        else:
            self.config = DecisionConfig()

        # 2. Subsystems
        self.signals_engine = RuntimeSignalsEngine()
        self.ml_predictor = AgentFailurePredictor()
        self.llm_judge = LLMJudge()
        self.decision_system = DecisionSystem(config=self.config)
        self.registry = tool_registry or ToolRegistry()
        self.intervention_engine = InterventionEngine(
            registry=self.registry,
            max_interventions_per_run=max_interventions,
        )

        # 3. Session State
        self.task_prompt: str = ""
        self.trajectory_history: List[Dict[str, Any]] = []
        self.audit_log: List[GuardStepResult] = []
        self.is_active: bool = False
        self.is_terminated: bool = False
        self.is_escalated: bool = False

    def start_session(self, task_prompt: str) -> None:
        """Start a new monitored agent session."""
        self.task_prompt = task_prompt
        self.trajectory_history.clear()
        self.audit_log.clear()
        self.signals_engine.reset(task_prompt=task_prompt)
        self.decision_system.reset()
        self.intervention_engine.reset()
        self.is_active = True
        self.is_terminated = False
        self.is_escalated = False
        logger.info(f"Started monitoring session for task: '{task_prompt[:80]}...'")

    def monitor_step(self, turn: Dict[str, Any]) -> GuardStepResult:
        """
        Execute full 10-step monitoring and intervention lifecycle for a single turn.

        Flow:
        1. Record action and observation.
        2. Signals Engine computes runtime metrics.
        3. ML Model predicts failure probability.
        4. LLM Judge produces structured diagnosis.
        5. Decision System combines outputs.
        6. If CONTINUE: allow agent to proceed.
        7. If ALARM: activate Intervention Layer.
        8. Apply intervention, terminate, or escalate.
        9. Resume monitoring on subsequent steps.
        """
        if not self.is_active:
            raise RuntimeError("Monitoring session not started. Call start_session() first.")

        if self.is_terminated:
            logger.warning("Step received after session termination. Forcing HALT.")
            return GuardStepResult(
                step_idx=len(self.trajectory_history),
                role=str(turn.get("role", "unknown")),
                decision=FinalDecision.ALARM,
                allow_proceed=False,
                ml_risk_prob=1.0,
                judge_verdict="ALARM",
                judge_category="UNKNOWN",
                judge_confidence=1.0,
                applied_rule="HALTED_AFTER_TERMINATION",
                decision_rationale="Session already terminated.",
            )

        # 1. Record in trajectory
        self.trajectory_history.append(turn)
        current_step_idx = len(self.trajectory_history) - 1
        role = str(turn.get("role", "unknown"))

        # If turn is from user, record prompt and allow execution to proceed normally
        if role == "user":
            result = GuardStepResult(
                step_idx=current_step_idx,
                role=role,
                decision=FinalDecision.CONTINUE,
                allow_proceed=True,
                ml_risk_prob=0.0,
                judge_verdict="CONTINUE",
                judge_category="UNKNOWN",
                judge_confidence=1.0,
                applied_rule="USER_INITIATIVE",
                decision_rationale="Initial user prompt recorded. Agent allowed to begin execution.",
            )
            self.audit_log.append(result)
            return result

        # 2. Signals Engine
        try:
            sig = self.signals_engine.update(turn)
        except Exception as e:
            logger.error(f"Signals Engine error at step {current_step_idx}: {e}")
            from src.signals.engine import SignalVector
            sig = SignalVector(
                step_idx=current_step_idx, role=role, is_agent_turn=1, is_env_turn=0,
                active_retry_count=0, cumulative_retries=0, is_retry_step=0, isolated_failure_flag=0,
                tool_failure_rate=0.0, consecutive_tool_failures=0, cum_tool_calls=0, cum_tool_errors=0,
                action_repetition_count=0, consecutive_same_action=0, content_repetition_score=0.0,
                loop_indicator_score=0.0, stagnation_score=0.0, lexical_diversity=1.0,
                cum_thought_words=0, reasoning_explosion_ratio=1.0, plan_mismatch_score=0.0,
                cum_task_drift_score=0.0, action_diversity=1.0, consecutive_agent_monologue=0,
                rule_risk_score=0.0
            )

        # 3. ML Risk Predictor
        try:
            ml_risk_p = self.ml_predictor.predict_risk(sig)
        except Exception as e:
            logger.error(f"ML Predictor error at step {current_step_idx}: {e}")
            ml_risk_p = 0.50  # Safe neutral default

        # 4. LLM Judge
        try:
            judge_res = self.llm_judge.judge_step(
                task_prompt=self.task_prompt,
                turns_prefix=self.trajectory_history,
                signals=sig,
                ml_risk_prob=ml_risk_p,
            )
        except Exception as e:
            logger.error(f"LLM Judge error at step {current_step_idx}: {e}")
            from src.judge.schema import JudgeConfidence, JudgeVerdict, ReasonCategory
            judge_res = JudgeResponse(
                verdict=JudgeVerdict.CONTINUE if ml_risk_p < 0.60 else JudgeVerdict.ALARM,
                reason_category=ReasonCategory.UNKNOWN,
                explanation="LLM Judge error fallback.",
                confidence=0.50,
                confidence_level=JudgeConfidence.LOW,
            )

        # 5. Decision System Fusion
        decision_rec = self.decision_system.decide(
            signals=sig,
            ml_risk_prob=ml_risk_p,
            judge_response=judge_res,
        )

        # 6. Evaluate Decision & Intervene
        intervention_outcome: Optional[InterventionOutcome] = None
        injected_feedback: Optional[Dict[str, Any]] = None
        allow_proceed = True

        if decision_rec.decision == FinalDecision.ALARM:
            intervention_outcome = self.intervention_engine.handle_alarm(
                decision_record=decision_rec,
                signals=sig,
                task_prompt=self.task_prompt,
                trajectory_history=self.trajectory_history,
            )

            # Check outcome status
            if intervention_outcome.action_type == InterventionActionType.TERMINATE:
                self.is_terminated = True
                allow_proceed = False
            elif intervention_outcome.action_type == InterventionActionType.ESCALATE_TO_HUMAN:
                self.is_escalated = True
                allow_proceed = False
            else:
                # Corrective action injected into trajectory context
                injected_feedback = intervention_outcome.injected_message
                if injected_feedback:
                    self.trajectory_history.append(injected_feedback)

        # 7. Record Step in Audit Trail
        result = GuardStepResult(
            step_idx=current_step_idx,
            role=role,
            decision=decision_rec.decision,
            allow_proceed=allow_proceed,
            ml_risk_prob=ml_risk_p,
            judge_verdict=judge_res.verdict.value,
            judge_category=judge_res.reason_category.value,
            judge_confidence=judge_res.confidence,
            applied_rule=decision_rec.applied_rule,
            decision_rationale=decision_rec.rationale,
            intervention=intervention_outcome,
            injected_feedback=injected_feedback,
        )
        self.audit_log.append(result)
        return result

    def run_trajectory(self, task_prompt: str, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Audit an entire trajectory sequentially."""
        self.start_session(task_prompt=task_prompt)
        step_results = []
        for turn in turns:
            res = self.monitor_step(turn)
            step_results.append(res)
            if not res.allow_proceed:
                logger.info(f"Execution halted at step {res.step_idx} due to {res.intervention.action_type.value if res.intervention else 'HALT'}")
                break

        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Produce comprehensive session summary."""
        total_steps = len(self.audit_log)
        alarms = sum(1 for s in self.audit_log if s.decision == FinalDecision.ALARM)
        interventions = sum(1 for s in self.audit_log if s.intervention is not None)

        action_counts = {}
        for s in self.audit_log:
            if s.intervention:
                act = s.intervention.action_type.value
                action_counts[act] = action_counts.get(act, 0) + 1

        return {
            "task_prompt": self.task_prompt[:120],
            "total_monitored_steps": total_steps,
            "total_alarms": alarms,
            "total_interventions": interventions,
            "is_terminated": self.is_terminated,
            "is_escalated": self.is_escalated,
            "intervention_breakdown": action_counts,
            "decision_summary": self.decision_system.get_summary(),
        }

    def export_audit_log(self, filepath: str) -> None:
        """Export session audit log to JSON."""
        data = [r.to_dict() for r in self.audit_log]
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Audit log exported to {filepath}")

