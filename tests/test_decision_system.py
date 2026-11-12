"""
Unit Tests for Phase 7 Decision-Fusion System.
Validates rule-based fusion, isolated failure suppression,
disagreement handling, threshold configurability, and audit logging.
"""

import os
import pytest
from src.decision.config import DecisionConfig
from src.decision.system import DecisionSystem, FinalDecision
from src.judge.schema import JudgeConfidence, JudgeResponse, JudgeVerdict, ReasonCategory
from src.signals.engine import SignalVector


def create_dummy_signals(**kwargs) -> SignalVector:
    """Helper to create dummy SignalVector with default healthy values."""
    defaults = {
        "step_idx": 1,
        "role": "assistant",
        "is_agent_turn": 1,
        "is_env_turn": 0,
        "active_retry_count": 0,
        "cumulative_retries": 0,
        "is_retry_step": 0,
        "isolated_failure_flag": 0,
        "tool_failure_rate": 0.0,
        "consecutive_tool_failures": 0,
        "cum_tool_calls": 1,
        "cum_tool_errors": 0,
        "action_repetition_count": 0,
        "consecutive_same_action": 0,
        "content_repetition_score": 0.0,
        "loop_indicator_score": 0.0,
        "stagnation_score": 0.0,
        "lexical_diversity": 1.0,
        "cum_thought_words": 50,
        "reasoning_explosion_ratio": 1.0,
        "plan_mismatch_score": 0.1,
        "cum_task_drift_score": 0.1,
        "action_diversity": 1.0,
        "consecutive_agent_monologue": 1,
        "rule_risk_score": 0.0,
    }
    defaults.update(kwargs)
    return SignalVector(**defaults)


def create_dummy_judge(
    verdict: JudgeVerdict,
    category: ReasonCategory,
    confidence: float = 0.80,
    confidence_level: JudgeConfidence = JudgeConfidence.HIGH,
) -> JudgeResponse:
    """Helper to create dummy JudgeResponse."""
    return JudgeResponse(
        verdict=verdict,
        reason_category=category,
        explanation="Test explanation.",
        confidence=confidence,
        confidence_level=confidence_level,
    )


def test_isolated_failure_is_suppressed():
    """First isolated tool failure without retries must produce CONTINUE."""
    ds = DecisionSystem()
    signals = create_dummy_signals(
        isolated_failure_flag=1,
        active_retry_count=0,
        cum_tool_errors=1,
        consecutive_tool_failures=1,
    )
    judge = create_dummy_judge(JudgeVerdict.ALARM, ReasonCategory.TEMPORARY_TIMEOUT, confidence=0.60)
    record = ds.decide(signals=signals, ml_risk_prob=0.55, judge_response=judge)

    assert record.decision == FinalDecision.CONTINUE
    assert record.applied_rule == "ISOLATED_FAILURE_SUPPRESSED"


def test_critical_retry_overflow_triggers_alarm():
    """Active retry count >= 3 triggers immediate ALARM regardless of others."""
    ds = DecisionSystem()
    signals = create_dummy_signals(active_retry_count=3)
    judge = create_dummy_judge(JudgeVerdict.CONTINUE, ReasonCategory.UNKNOWN, confidence=0.90)
    record = ds.decide(signals=signals, ml_risk_prob=0.20, judge_response=judge)

    assert record.decision == FinalDecision.ALARM
    assert record.applied_rule == "CRITICAL_RETRY_OVERFLOW"


def test_critical_dead_loop_triggers_alarm():
    """Loop indicator >= 0.85 triggers immediate ALARM."""
    ds = DecisionSystem()
    signals = create_dummy_signals(loop_indicator_score=0.90)
    judge = create_dummy_judge(JudgeVerdict.CONTINUE, ReasonCategory.UNKNOWN, confidence=0.85)
    record = ds.decide(signals=signals, ml_risk_prob=0.30, judge_response=judge)

    assert record.decision == FinalDecision.ALARM
    assert record.applied_rule == "CRITICAL_DEAD_LOOP"


def test_unanimous_alarm():
    """Both ML high and Judge ALARM -> ALARM."""
    ds = DecisionSystem()
    signals = create_dummy_signals()
    judge = create_dummy_judge(JudgeVerdict.ALARM, ReasonCategory.TOOL_FAILURE, confidence=0.85)
    record = ds.decide(signals=signals, ml_risk_prob=0.75, judge_response=judge)

    assert record.decision == FinalDecision.ALARM
    assert record.applied_rule == "UNANIMOUS_ALARM"


def test_unanimous_continue():
    """Both ML low and Judge CONTINUE -> CONTINUE."""
    ds = DecisionSystem()
    signals = create_dummy_signals()
    judge = create_dummy_judge(JudgeVerdict.CONTINUE, ReasonCategory.UNKNOWN, confidence=0.85)
    record = ds.decide(signals=signals, ml_risk_prob=0.20, judge_response=judge)

    assert record.decision == FinalDecision.CONTINUE
    assert record.applied_rule == "UNANIMOUS_CONTINUE"


def test_disagreement_ml_high_judge_continue_with_high_confidence():
    """ML high (0.65), Judge CONTINUE (confidence=0.85, TEMPORARY_TIMEOUT) -> CONTINUE."""
    ds = DecisionSystem()
    signals = create_dummy_signals()
    judge = create_dummy_judge(JudgeVerdict.CONTINUE, ReasonCategory.TEMPORARY_TIMEOUT, confidence=0.85)
    record = ds.decide(signals=signals, ml_risk_prob=0.65, judge_response=judge)

    assert record.decision == FinalDecision.CONTINUE
    assert record.applied_rule == "JUDGE_SEMANTIC_RESCUE"


def test_disagreement_ml_high_judge_continue_with_low_confidence():
    """ML high (0.65), Judge CONTINUE (confidence=0.55) -> ALARM (fails safe)."""
    ds = DecisionSystem()
    signals = create_dummy_signals()
    judge = create_dummy_judge(JudgeVerdict.CONTINUE, ReasonCategory.UNKNOWN, confidence=0.55)
    record = ds.decide(signals=signals, ml_risk_prob=0.65, judge_response=judge)

    assert record.decision == FinalDecision.ALARM
    assert record.applied_rule == "ML_HIGH_RISK_DOMINANCE"


def test_disagreement_ml_low_judge_alarm_high_confidence_plan_mismatch():
    """ML low (0.25), Judge ALARM (confidence=0.85, PLAN_MISMATCH) -> ALARM."""
    ds = DecisionSystem()
    signals = create_dummy_signals()
    judge = create_dummy_judge(JudgeVerdict.ALARM, ReasonCategory.PLAN_MISMATCH, confidence=0.85)
    record = ds.decide(signals=signals, ml_risk_prob=0.25, judge_response=judge)

    assert record.decision == FinalDecision.ALARM
    assert record.applied_rule == "JUDGE_SEMANTIC_ALARM"


def test_disagreement_ml_low_judge_alarm_low_confidence():
    """ML low (0.20), Judge ALARM with low confidence (0.45) -> CONTINUE."""
    ds = DecisionSystem()
    signals = create_dummy_signals()
    judge = create_dummy_judge(JudgeVerdict.ALARM, ReasonCategory.UNKNOWN, confidence=0.45)
    record = ds.decide(signals=signals, ml_risk_prob=0.20, judge_response=judge)

    assert record.decision == FinalDecision.CONTINUE
    assert record.applied_rule == "DISCOUNT_LOW_CONFIDENCE_JUDGE"


def test_configurable_thresholds_from_yaml():
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "configs", "decision_config.yaml")
    cfg = DecisionConfig.from_yaml(yaml_path)
    assert cfg.max_retries_threshold == 3
    assert cfg.ml_alarm_threshold == 0.60
    assert cfg.critical_loop_threshold == 0.85


def test_audit_logging_and_summary():
    ds = DecisionSystem()
    signals = create_dummy_signals()
    judge = create_dummy_judge(JudgeVerdict.CONTINUE, ReasonCategory.UNKNOWN, confidence=0.90)

    ds.decide(signals, 0.10, judge)
    ds.decide(signals, 0.20, judge)
    assert len(ds.decision_history) == 2

    summary = ds.get_summary()
    assert summary["total_decisions"] == 2
    assert summary["continues"] == 2
    assert summary["alarms"] == 0

