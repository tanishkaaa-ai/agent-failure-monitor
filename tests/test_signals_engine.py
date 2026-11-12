"""
Unit and Integration Tests for Phase 4 Signals Engine.
Validates retry count mechanics, isolated failure handling, loop detection,
stagnation scores, and real trajectory execution.
"""

import json
import pandas as pd
import pytest
from src.signals.engine import RuntimeSignalsEngine, SignalVector


def test_first_tool_failure_keeps_retry_zero():
    """
    Test requirement: Handle first tool failure correctly.
    Retry count must remain 0 when a tool fails until a retry is actually attempted.
    Isolated failure should not spike risk alarm.
    """
    engine = RuntimeSignalsEngine(task_prompt="Fetch weather data for London")

    # Step 0: User prompt
    s0 = engine.update({"role": "user", "thought": "", "action": "", "content": "Fetch weather"})
    assert s0.active_retry_count == 0
    assert s0.cumulative_retries == 0

    # Step 1: Agent calls weather tool
    action_1 = json.dumps([{"name": "get_weather", "arguments": "London"}])
    s1 = engine.update({"role": "assistant", "thought": "Calling API", "action": action_1, "content": ""})
    assert s1.active_retry_count == 0
    assert s1.cumulative_retries == 0
    assert s1.is_retry_step == 0

    # Step 2: Tool execution fails in environment (First failure!)
    s2 = engine.update({"role": "environment", "thought": "", "action": "", "content": "Error 500: Server Timeout"})
    assert s2.consecutive_tool_failures == 1
    # RETRY COUNT MUST REMAIN ZERO HERE!
    assert s2.active_retry_count == 0, "active_retry_count should be 0 on first failure before agent retries"
    assert s2.cumulative_retries == 0, "cumulative_retries should be 0 on first failure"
    assert s2.isolated_failure_flag == 1, "Must flag as isolated first failure"
    assert s2.rule_risk_score <= 0.25, "Must not trigger high alarm on isolated first failure"


def test_retry_increments_when_agent_retries_failed_tool():
    """
    Test requirement: Retry count increments only when the agent re-executes the failing tool.
    """
    engine = RuntimeSignalsEngine(task_prompt="Query database")

    # Call db_query
    act = json.dumps([{"name": "db_query", "arguments": "SELECT *"}])
    engine.update({"role": "assistant", "thought": "Querying", "action": act, "content": ""})

    # Tool fails
    s_fail = engine.update({"role": "environment", "thought": "", "action": "", "content": "DatabaseError: Connection lost"})
    assert s_fail.active_retry_count == 0
    assert s_fail.consecutive_tool_failures == 1

    # Agent retries db_query
    s_retry1 = engine.update({"role": "assistant", "thought": "Retrying connection", "action": act, "content": ""})
    assert s_retry1.active_retry_count == 1
    assert s_retry1.cumulative_retries == 1
    assert s_retry1.is_retry_step == 1

    # Second failure
    s_fail2 = engine.update({"role": "environment", "thought": "", "action": "", "content": "DatabaseError: Still down"})
    assert s_fail2.consecutive_tool_failures == 2
    assert s_fail2.active_retry_count == 1

    # Second retry
    s_retry2 = engine.update({"role": "assistant", "thought": "Retrying with timeout", "action": act, "content": ""})
    assert s_retry2.active_retry_count == 2
    assert s_retry2.cumulative_retries == 2


def test_tool_switch_aborts_active_retry_chain():
    """If agent decides to switch to a fallback tool instead of retrying, active_retry_count clears."""
    engine = RuntimeSignalsEngine(task_prompt="Search web")
    act_google = json.dumps([{"name": "google_search", "arguments": "AI news"}])
    act_bing = json.dumps([{"name": "bing_search", "arguments": "AI news"}])

    engine.update({"role": "assistant", "thought": "", "action": act_google, "content": ""})
    engine.update({"role": "environment", "thought": "", "action": "", "content": "API Rate Limit Exceeded: error 429"})

    # Agent uses bing_search instead of retrying google_search
    s_switch = engine.update({"role": "assistant", "thought": "Trying fallback", "action": act_bing, "content": ""})
    assert s_switch.active_retry_count == 0, "Switching tools should not count as retrying google_search"
    assert s_switch.is_retry_step == 0


def test_loop_and_repetition_detection():
    """Detects repeated identical actions."""
    engine = RuntimeSignalsEngine(task_prompt="Solve task")
    repeated_action = json.dumps([{"name": "calc", "arguments": "1+1"}])

    engine.update({"role": "assistant", "thought": "", "action": repeated_action, "content": ""})
    engine.update({"role": "environment", "thought": "", "action": "", "content": "2"})

    # Repeat exact same action
    s_rep = engine.update({"role": "assistant", "thought": "", "action": repeated_action, "content": ""})
    assert s_rep.action_repetition_count == 1
    assert s_rep.loop_indicator_score > 0.3


def test_stagnation_detection():
    """Tests stagnation score over a 3-turn window."""
    engine = RuntimeSignalsEngine(task_prompt="Do something")
    engine.update({"role": "assistant", "thought": "", "action": "", "content": ""})
    engine.update({"role": "assistant", "thought": "", "action": "", "content": ""})
    s = engine.update({"role": "assistant", "thought": "", "action": "", "content": ""})
    assert s.stagnation_score == 1.0


def test_streaming_and_batch_parity():
    """Verifies that step-by-step update matches evaluate_prefix exactly."""
    turns = [
        {"role": "user", "thought": "", "action": "", "content": "Compute sum"},
        {"role": "assistant", "thought": "Adding numbers", "action": json.dumps([{"name": "add", "arguments": "2,3"}]), "content": ""},
        {"role": "environment", "thought": "", "action": "", "content": "5"},
        {"role": "assistant", "thought": "Done", "action": "", "content": "Result is 5"}
    ]
    engine_stream = RuntimeSignalsEngine(task_prompt="Compute sum")
    stream_results = [engine_stream.update(t) for t in turns]

    engine_batch = RuntimeSignalsEngine(task_prompt="Compute sum")
    batch_results = engine_batch.evaluate_prefix(turns, task_prompt="Compute sum")

    assert len(stream_results) == len(batch_results)
    for s_res, b_res in zip(stream_results, batch_results):
        assert s_res.to_features_dict() == b_res.to_features_dict()


def test_real_aftraj_unsafe_trajectory():
    """Executes on an actual trajectory from aftraj_unsafe.parquet."""
    unsafe_df = pd.read_parquet("data/raw/aftraj_unsafe.parquet")
    sample = unsafe_df.iloc[0]

    engine = RuntimeSignalsEngine(task_prompt=str(sample["task"]))
    signals = engine.evaluate_prefix(list(sample["turns"]))

    assert len(signals) == len(sample["turns"])
    for s in signals:
        assert isinstance(s, SignalVector)
        vec = s.to_numpy()
        assert len(vec) == len(SignalVector.feature_names())
        assert not any(pd.isna(v) for v in vec)

