"""
Phase 7: Decision System
Rule-based fusion engine combining runtime signals, ML failure risk, and LLM Judge output
into a single deterministic CONTINUE or ALARM verdict.
"""

from dataclasses import asdict, dataclass
from enum import Enum
import logging
import os
from typing import Any, Dict, List, Optional

from src.decision.config import DecisionConfig
from src.judge.schema import JudgeConfidence, JudgeResponse, JudgeVerdict, ReasonCategory
from src.signals.engine import SignalVector

logger = logging.getLogger("decision_system")


class FinalDecision(str, Enum):
    CONTINUE = "CONTINUE"
    ALARM = "ALARM"


@dataclass
class DecisionRecord:
    """Detailed audit record for a single execution step decision."""
    step_idx: int
    decision: FinalDecision
    applied_rule: str
    rationale: str

    # Source Inputs
    ml_risk_prob: float
    judge_verdict: str
    judge_category: str
    judge_confidence: float

    # Key Signal Snapshots
    active_retries: int
    consecutive_tool_failures: int
    loop_score: float
    stagnation_score: float
    isolated_failure: bool

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value
        return d


class DecisionSystem:
    """
    Deterministic rule-based decision-fusion engine.
    Fuses Signals Engine metrics, ML predicted risk, and LLM Judge verdict.
    """

    def __init__(self, config: Optional[DecisionConfig] = None):
        self.config = config or DecisionConfig()
        self.decision_history: List[DecisionRecord] = []

    def decide(
        self,
        signals: SignalVector,
        ml_risk_prob: float,
        judge_response: JudgeResponse,
    ) -> DecisionRecord:
        """
        Evaluate inputs using prioritized deterministic fusion rules.

        Priority 1: Hard Critical Signal Overrides (immediate alarm)
        Priority 2: Isolated Failure Protection (suppress false alarm on single transient error)
        Priority 3: Unanimous Agreement (ML and Judge agree)
        Priority 4: Disagreement Resolution (semantic vs. statistical trade-offs)
        Priority 5: Ambiguous / Borderline Zone (Judge as decisive tiebreaker)
        """
        step = signals.step_idx

        # -------------------------------------------------------------
        # Priority 1: Hard Critical Runtime Overrides
        # -------------------------------------------------------------
        if signals.active_retry_count >= self.config.max_retries_threshold:
            return self._record(
                step_idx=step,
                decision=FinalDecision.ALARM,
                rule="CRITICAL_RETRY_OVERFLOW",
                rationale=(
                    f"Agent exceeded maximum allowed retries ({signals.active_retry_count} >= "
                    f"{self.config.max_retries_threshold}) on failing tool."
                ),
                signals=signals,
                ml_prob=ml_risk_prob,
                judge=judge_response,
            )

        if signals.consecutive_tool_failures >= self.config.max_consecutive_failures:
            return self._record(
                step_idx=step,
                decision=FinalDecision.ALARM,
                rule="CRITICAL_CONSECUTIVE_FAILURES",
                rationale=(
                    f"Agent suffered {signals.consecutive_tool_failures} consecutive unrecovered tool errors "
                    f"(limit: {self.config.max_consecutive_failures})."
                ),
                signals=signals,
                ml_prob=ml_risk_prob,
                judge=judge_response,
            )

        if signals.loop_indicator_score >= self.config.critical_loop_threshold:
            return self._record(
                step_idx=step,
                decision=FinalDecision.ALARM,
                rule="CRITICAL_DEAD_LOOP",
                rationale=(
                    f"Critical repetitive loop detected (score: {signals.loop_indicator_score:.2f} >= "
                    f"{self.config.critical_loop_threshold:.2f})."
                ),
                signals=signals,
                ml_prob=ml_risk_prob,
                judge=judge_response,
            )

        if signals.stagnation_score >= self.config.critical_stagnation_threshold:
            return self._record(
                step_idx=step,
                decision=FinalDecision.ALARM,
                rule="CRITICAL_STAGNATION",
                rationale=(
                    f"Execution is completely stagnant with zero forward progress across recent turns "
                    f"(score: {signals.stagnation_score:.2f})."
                ),
                signals=signals,
                ml_prob=ml_risk_prob,
                judge=judge_response,
            )

        # -------------------------------------------------------------
        # Priority 2: Isolated Failure Protection (False Alarm Suppression)
        # -------------------------------------------------------------
        if bool(signals.isolated_failure_flag) and signals.active_retry_count == 0:
            if ml_risk_prob < self.config.ml_override_threshold:
                return self._record(
                    step_idx=step,
                    decision=FinalDecision.CONTINUE,
                    rule="ISOLATED_FAILURE_SUPPRESSED",
                    rationale=(
                        "First isolated tool failure encountered. Suppressing alarm until agent actively retries "
                        "or enters a loop (retry_count=0)."
                    ),
                    signals=signals,
                    ml_prob=ml_risk_prob,
                    judge=judge_response,
                )

        # -------------------------------------------------------------
        # Priority 3: Unanimous Agreement
        # -------------------------------------------------------------
        ml_high = ml_risk_prob >= self.config.ml_alarm_threshold
        ml_low = ml_risk_prob < self.config.ml_continue_threshold
        judge_alarm = judge_response.verdict == JudgeVerdict.ALARM
        judge_continue = judge_response.verdict == JudgeVerdict.CONTINUE

        if ml_high and judge_alarm:
            return self._record(
                step_idx=step,
                decision=FinalDecision.ALARM,
                rule="UNANIMOUS_ALARM",
                rationale=(
                    f"Both ML model (risk p={ml_risk_prob:.2f}) and LLM Judge ({judge_response.reason_category.value}, "
                    f"confidence={judge_response.confidence:.2f}) agree failure is unfolding."
                ),
                signals=signals,
                ml_prob=ml_risk_prob,
                judge=judge_response,
            )

        if ml_low and judge_continue:
            return self._record(
                step_idx=step,
                decision=FinalDecision.CONTINUE,
                rule="UNANIMOUS_CONTINUE",
                rationale=(
                    f"Both ML model (risk p={ml_risk_prob:.2f}) and LLM Judge confirm healthy execution "
                    f"(confidence={judge_response.confidence:.2f})."
                ),
                signals=signals,
                ml_prob=ml_risk_prob,
                judge=judge_response,
            )

        # -------------------------------------------------------------
        # Priority 4: Disagreement Resolution
        # -------------------------------------------------------------
        # Case 4A: ML says ALARM (high risk), but LLM Judge says CONTINUE
        if ml_high and judge_continue:
            if ml_risk_prob >= self.config.ml_override_threshold:
                return self._record(
                    step_idx=step,
                    decision=FinalDecision.ALARM,
                    rule="ML_OVERRIDE_EXTREME_RISK",
                    rationale=(
                        f"Statistical ML failure risk is extraordinarily severe (p={ml_risk_prob:.2f} >= "
                        f"{self.config.ml_override_threshold:.2f}). Overriding Judge CONTINUE to maintain safety."
                    ),
                    signals=signals,
                    ml_prob=ml_risk_prob,
                    judge=judge_response,
                )

            if (
                judge_response.confidence >= self.config.llm_high_confidence
                and judge_response.reason_category in (ReasonCategory.TEMPORARY_TIMEOUT, ReasonCategory.UNKNOWN)
            ):
                return self._record(
                    step_idx=step,
                    decision=FinalDecision.CONTINUE,
                    rule="JUDGE_SEMANTIC_RESCUE",
                    rationale=(
                        f"High-confidence LLM Judge ({judge_response.confidence:.2f}) verified that execution is benign "
                        f"or recovering from transient delay, overriding statistical ML risk (p={ml_risk_prob:.2f})."
                    ),
                    signals=signals,
                    ml_prob=ml_risk_prob,
                    judge=judge_response,
                )

            # Default to safety if Judge is not high confidence
            return self._record(
                step_idx=step,
                decision=FinalDecision.ALARM,
                rule="ML_HIGH_RISK_DOMINANCE",
                rationale=(
                    f"ML model indicates elevated risk (p={ml_risk_prob:.2f}), and LLM Judge lacks sufficient confidence "
                    f"({judge_response.confidence:.2f} < {self.config.llm_high_confidence:.2f}) to overrule. Fails safe."
                ),
                signals=signals,
                ml_prob=ml_risk_prob,
                judge=judge_response,
            )

        # Case 4B: ML says CONTINUE (low risk), but LLM Judge says ALARM
        if ml_low and judge_alarm:
            if (
                judge_response.confidence >= self.config.llm_high_confidence
                and judge_response.reason_category in (ReasonCategory.PLAN_MISMATCH, ReasonCategory.TOOL_FAILURE, ReasonCategory.LOOP)
            ):
                return self._record(
                    step_idx=step,
                    decision=FinalDecision.ALARM,
                    rule="JUDGE_SEMANTIC_ALARM",
                    rationale=(
                        f"High-confidence LLM Judge ({judge_response.confidence:.2f}) identified qualitative/semantic "
                        f"failure ({judge_response.reason_category.value}) undetectable by low statistical signals (p={ml_risk_prob:.2f})."
                    ),
                    signals=signals,
                    ml_prob=ml_risk_prob,
                    judge=judge_response,
                )

            if judge_response.confidence < self.config.llm_low_confidence:
                return self._record(
                    step_idx=step,
                    decision=FinalDecision.CONTINUE,
                    rule="DISCOUNT_LOW_CONFIDENCE_JUDGE",
                    rationale=(
                        f"LLM Judge ALARM is low-confidence ({judge_response.confidence:.2f} < {self.config.llm_low_confidence:.2f}). "
                        f"Favoring non-disruptive execution as statistical ML risk is low (p={ml_risk_prob:.2f})."
                    ),
                    signals=signals,
                    ml_prob=ml_risk_prob,
                    judge=judge_response,
                )

            # Moderate confidence: corroborate with signals
            is_corroborated = (
                signals.cum_task_drift_score > 0.65
                or signals.active_retry_count >= 1
                or signals.tool_failure_rate > 0.30
            )
            if is_corroborated:
                return self._record(
                    step_idx=step,
                    decision=FinalDecision.ALARM,
                    rule="CORROBORATED_JUDGE_ALARM",
                    rationale=(
                        f"LLM Judge ALARM ({judge_response.reason_category.value}) corroborated by supporting runtime signals "
                        f"(drift={signals.cum_task_drift_score:.2f}, retries={signals.active_retry_count})."
                    ),
                    signals=signals,
                    ml_prob=ml_risk_prob,
                    judge=judge_response,
                )
            else:
                return self._record(
                    step_idx=step,
                    decision=FinalDecision.CONTINUE,
                    rule="BENIGN_UNVERIFIED_WARNING",
                    rationale=(
                        f"LLM Judge ALARM is uncorroborated by runtime metrics, and ML risk is low (p={ml_risk_prob:.2f}). "
                        "Continuing."
                    ),
                    signals=signals,
                    ml_prob=ml_risk_prob,
                    judge=judge_response,
                )

        # -------------------------------------------------------------
        # Priority 5: Ambiguous / Borderline Zone (0.35 <= p < 0.60)
        # -------------------------------------------------------------
        # In the uncertain ML zone, the LLM Judge serves as the decisive tiebreaker
        if judge_alarm and judge_response.confidence >= self.config.llm_low_confidence:
            return self._record(
                step_idx=step,
                decision=FinalDecision.ALARM,
                rule="JUDGE_TIEBREAKER_ALARM",
                rationale=(
                    f"ML model is in ambiguous boundary zone (p={ml_risk_prob:.2f}). LLM Judge acts as tiebreaker "
                    f"and alarms on {judge_response.reason_category.value} (conf={judge_response.confidence:.2f})."
                ),
                signals=signals,
                ml_prob=ml_risk_prob,
                judge=judge_response,
            )

        return self._record(
            step_idx=step,
            decision=FinalDecision.CONTINUE,
            rule="JUDGE_TIEBREAKER_CONTINUE",
            rationale=(
                f"ML model is in ambiguous boundary zone (p={ml_risk_prob:.2f}), but LLM Judge or signals do not "
                "substantiate an alarm. Safe to proceed."
            ),
            signals=signals,
            ml_prob=ml_risk_prob,
            judge=judge_response,
        )

    def _record(
        self,
        step_idx: int,
        decision: FinalDecision,
        rule: str,
        rationale: str,
        signals: SignalVector,
        ml_prob: float,
        judge: JudgeResponse,
    ) -> DecisionRecord:
        record = DecisionRecord(
            step_idx=step_idx,
            decision=decision,
            applied_rule=rule,
            rationale=rationale,
            ml_risk_prob=round(ml_prob, 4),
            judge_verdict=judge.verdict.value,
            judge_category=judge.reason_category.value,
            judge_confidence=round(judge.confidence, 4),
            active_retries=signals.active_retry_count,
            consecutive_tool_failures=signals.consecutive_tool_failures,
            loop_score=round(signals.loop_indicator_score, 4),
            stagnation_score=round(signals.stagnation_score, 4),
            isolated_failure=bool(signals.isolated_failure_flag),
        )
        self.decision_history.append(record)

        if self.config.log_decisions:
            logger.info(
                f"[Step {step_idx}] DECISION: {decision.value} | Rule: {rule} | ML_p={ml_prob:.2f} | "
                f"Judge={judge.verdict.value} ({judge.reason_category.value}) | Rationale: {rationale}"
            )
        return record

    def reset(self) -> None:
        """Reset decision history."""
        self.decision_history.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Summary statistics of all decisions made in current session."""
        total = len(self.decision_history)
        alarms = sum(1 for d in self.decision_history if d.decision == FinalDecision.ALARM)
        continues = total - alarms
        rules_applied = {}
        for d in self.decision_history:
            rules_applied[d.applied_rule] = rules_applied.get(d.applied_rule, 0) + 1

        return {
            "total_decisions": total,
            "alarms": alarms,
            "continues": continues,
            "alarm_rate": round(alarms / max(1, total), 4),
            "rules_applied": rules_applied,
        }

