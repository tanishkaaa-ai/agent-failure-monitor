"""
Unit Tests for Phase 8 Intervention Layer.
Validates category mapping, tool switching, registry lookups,
retry limits, and budget exhaustion.
"""

import pytest
from src.decision.system import DecisionRecord, FinalDecision
from src.interventions.actions import InterventionActionType, InterventionOutcome
from src.interventions.engine import InterventionEngine
from src.interventions.registry import ToolRegistry
from src.signals.engine import SignalVector


def make_dummy_signals(**kwargs) -> SignalVector:
    defaults = {
        "step_idx": 5, "role": "assistant", "is_agent_turn": 1, "is_env_turn": 0,
        "active_retry_count": 1, "cumulative_retries": 1, "is_retry_step": 1,
        "isolated_failure_flag": 0, "tool_failure_rate": 0.5, "consecutive_tool_failures": 1,
        "cum_tool_calls": 2, "cum_tool_errors": 1, "action_repetition_count": 0,
        "consecutive_same_action": 0, "content_repetition_score": 0.0, "loop_indicator_score": 0.0,
        "stagnation_score": 0.0, "lexical_diversity": 1.0, "cum_thought_words": 100,
        "reasoning_explosion_ratio": 1.0, "plan_mismatch_score": 0.1, "cum_task_drift_score": 0.1,
        "action_diversity": 1.0, "consecutive_agent_monologue": 1, "rule_risk_score": 0.5,
    }
    defaults.update(kwargs)
    return SignalVector(**defaults)


def make_dummy_alarm_record(category: str, ml_prob: float = 0.70) -> DecisionRecord:
    return DecisionRecord(
        step_idx=5,
        decision=FinalDecision.ALARM,
        applied_rule="TEST_ALARM",
        rationale="Simulated test alarm",
        ml_risk_prob=ml_prob,
        judge_verdict="ALARM",
        judge_category=category,
        judge_confidence=0.85,
        active_retries=1,
        consecutive_tool_failures=1,
        loop_score=0.0,
        stagnation_score=0.0,
        isolated_failure=False,
    )


def test_reject_continue_decision():
    """InterventionEngine must not activate on CONTINUE."""
    engine = InterventionEngine()
    cont_record = DecisionRecord(
        step_idx=1, decision=FinalDecision.CONTINUE, applied_rule="NONE", rationale="",
        ml_risk_prob=0.1, judge_verdict="CONTINUE", judge_category="UNKNOWN",
        judge_confidence=0.9, active_retries=0, consecutive_tool_failures=0,
        loop_score=0.0, stagnation_score=0.0, isolated_failure=False
    )
    with pytest.raises(ValueError):
        engine.handle_alarm(cont_record, make_dummy_signals(), "Do task")


def test_temporary_timeout_retries_with_backoff():
    engine = InterventionEngine(max_retries_per_tool=2)
    record = make_dummy_alarm_record("TEMPORARY_TIMEOUT")
    signals = make_dummy_signals()
    history = [{"role": "assistant", "action": '[{"name": "google_search", "arguments": "query"}]'}]

    outcome = engine.handle_alarm(record, signals, "Do task", history)
    assert outcome.action_type == InterventionActionType.RETRY_WITH_BACKOFF
    assert outcome.status == "APPLIED"
    assert "backoff" in outcome.details.lower()
    assert outcome.injected_message is not None


def test_tool_failure_with_registered_fallback():
    """Tool 'compute' has registered fallback 'python_interpreter'."""
    engine = InterventionEngine()
    record = make_dummy_alarm_record("TOOL_FAILURE")
    signals = make_dummy_signals()
    history = [{"role": "assistant", "action": '[{"name": "compute", "arguments": "2+2"}]'}]

    outcome = engine.handle_alarm(record, signals, "Do task", history)
    assert outcome.action_type == InterventionActionType.SWITCH_TOOL
    assert outcome.status == "APPLIED"
    assert "python_interpreter" in outcome.details


def test_tool_failure_without_registered_fallback_escalates():
    """Tool 'run_tests' has NO registered fallback; must escalate to human."""
    engine = InterventionEngine()
    record = make_dummy_alarm_record("TOOL_FAILURE")
    signals = make_dummy_signals()
    history = [{"role": "assistant", "action": '[{"name": "run_tests", "arguments": "test.py"}]'}]

    outcome = engine.handle_alarm(record, signals, "Do task", history)
    assert outcome.action_type == InterventionActionType.ESCALATE_TO_HUMAN
    assert outcome.status == "ESCALATED"
    assert "no alternative tool" in outcome.details.lower()


def test_loop_action_mapping():
    engine = InterventionEngine()
    record = make_dummy_alarm_record("LOOP")
    outcome = engine.handle_alarm(record, make_dummy_signals(), "Do task")
    assert outcome.action_type == InterventionActionType.BREAK_LOOP_AND_REPLAN
    assert outcome.status == "APPLIED"


def test_plan_mismatch_action_mapping():
    engine = InterventionEngine()
    record = make_dummy_alarm_record("PLAN_MISMATCH")
    outcome = engine.handle_alarm(record, make_dummy_signals(), "Calculate 100 factorial")
    assert outcome.action_type == InterventionActionType.REPLAN
    assert "Calculate 100 factorial" in outcome.injected_message["content"]


def test_budget_exhaustion_terminates_run():
    engine = InterventionEngine(max_interventions_per_run=2)
    record = make_dummy_alarm_record("LOOP")
    signals = make_dummy_signals()

    # Apply 2 interventions to fill budget
    engine.handle_alarm(record, signals, "Task")
    engine.handle_alarm(record, signals, "Task")

    # 3rd intervention must TERMINATE
    outcome = engine.handle_alarm(record, signals, "Task")
    assert outcome.action_type == InterventionActionType.TERMINATE
    assert outcome.status == "TERMINATED"

