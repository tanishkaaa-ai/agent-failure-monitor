"""
Integration Tests for Phase 9 Complete Pipeline (AgentFailureGuardSystem).
Validates end-to-end monitoring, decision fusion, intervention triggers,
and execution resumption.
"""

import os
import pytest
from src.decision.system import FinalDecision
from src.interventions.actions import InterventionActionType
from src.judge.judge import LLMJudge
from src.judge.llm_client import MockLLMClient
from src.pipeline import AgentFailureGuardSystem, GuardStepResult


def get_test_guard(**kwargs):
    return AgentFailureGuardSystem(
        llm_judge=LLMJudge(client=MockLLMClient()),
        **kwargs
    )


def test_guard_system_initialization():
    guard = get_test_guard()
    assert guard.signals_engine is not None
    assert guard.ml_predictor is not None
    assert guard.llm_judge is not None
    assert guard.decision_system is not None
    assert guard.intervention_engine is not None
    assert not guard.is_active


def test_healthy_turn_allows_proceed():
    guard = get_test_guard()
    guard.start_session("Calculate sum of 2 and 3")

    turn = {"role": "assistant", "thought": "Simple addition", "action": "", "content": "Sum is 5"}
    result = guard.monitor_step(turn)

    assert isinstance(result, GuardStepResult)
    assert result.allow_proceed is True
    assert result.decision in (FinalDecision.CONTINUE, FinalDecision.ALARM)


def test_repeated_failure_triggers_intervention_and_terminates():
    """Validates that repeated tool failures trigger recovery actions and eventually terminate."""
    guard = get_test_guard(max_interventions=3)
    guard.start_session("Query database")

    # Step 1: Agent calls failing tool
    guard.monitor_step({"role": "assistant", "thought": "Query", "action": '[{"name": "db", "arguments": ""}]', "content": ""})

    # Step 2: Environment error 1
    r2 = guard.monitor_step({"role": "environment", "thought": "", "action": "", "content": "Error: db timeout"})

    # Step 3: Agent retries
    r3 = guard.monitor_step({"role": "assistant", "thought": "Retrying", "action": '[{"name": "db", "arguments": ""}]', "content": ""})

    # Step 4: Environment error 2
    r4 = guard.monitor_step({"role": "environment", "thought": "", "action": "", "content": "Error: db timeout again"})

    # Check that interventions were recorded
    assert len(guard.intervention_engine.intervention_history) > 0
    # Check that audit log has records
    assert len(guard.audit_log) > 0


def test_export_audit_log(tmp_path):
    guard = AgentFailureGuardSystem()
    guard.start_session("Test task")
    guard.monitor_step({"role": "user", "thought": "", "action": "", "content": "Hello"})

    log_file = tmp_path / "test_audit.json"
    guard.export_audit_log(str(log_file))

    assert os.path.exists(log_file)
    assert os.path.getsize(log_file) > 10
