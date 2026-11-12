"""
Unit Tests for Phase 6 LLM Judge Component.
Validates Pydantic schema validation, mock client behavior,
error handling, and end-to-end integration.
"""

import json
import pytest
from src.judge.judge import LLMJudge, clean_json_text
from src.judge.llm_client import BaseLLMClient, MockLLMClient
from src.judge.schema import (
    JudgeConfidence,
    JudgeResponse,
    JudgeVerdict,
    ReasonCategory,
)
from src.signals.engine import RuntimeSignalsEngine


class FaultyLLMClient(BaseLLMClient):
    """Client that simulates network timeouts or broken API responses."""
    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 15.0) -> str:
        raise ConnectionError("Simulated network timeout")


class MalformedJSONClient(BaseLLMClient):
    """Client that returns invalid JSON text."""
    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 15.0) -> str:
        return "I think the agent should alarm because of an error."


def test_schema_valid_response():
    data = {
        "verdict": "ALARM",
        "reason_category": "TOOL_FAILURE",
        "explanation": "Tool failed repeatedly with 500 status.",
        "confidence": 0.85,
        "confidence_level": "HIGH"
    }
    resp = JudgeResponse(**data)
    assert resp.verdict == JudgeVerdict.ALARM
    assert resp.reason_category == ReasonCategory.TOOL_FAILURE
    assert resp.confidence == 0.85
    assert resp.confidence_level == JudgeConfidence.HIGH


def test_schema_invalid_confidence():
    data = {
        "verdict": "CONTINUE",
        "reason_category": "UNKNOWN",
        "explanation": "Healthy run.",
        "confidence": 1.5,  # Out of bounds!
    }
    with pytest.raises(Exception):
        JudgeResponse(**data)


def test_clean_json_text():
    raw_markdown = '```json\n{"verdict": "CONTINUE", "reason_category": "UNKNOWN"}\n```'
    cleaned = clean_json_text(raw_markdown)
    assert cleaned == '{"verdict": "CONTINUE", "reason_category": "UNKNOWN"}'


def test_mock_judge_healthy_step():
    engine = RuntimeSignalsEngine(task_prompt="Calculate sum")
    sig = engine.update({"role": "assistant", "thought": "Adding numbers", "action": "", "content": "Sum is 5"})

    judge = LLMJudge(client=MockLLMClient())
    resp = judge.judge_step(
        task_prompt="Calculate sum",
        turns_prefix=[{"role": "assistant", "thought": "Adding numbers", "action": "", "content": "Sum is 5"}],
        signals=sig,
        ml_risk_prob=0.15,
    )

    assert isinstance(resp, JudgeResponse)
    assert resp.verdict == JudgeVerdict.CONTINUE
    assert resp.confidence >= 0.0 and resp.confidence <= 1.0


def test_mock_judge_failure_alarm():
    engine = RuntimeSignalsEngine(task_prompt="Run query")
    engine.update({"role": "assistant", "thought": "", "action": '[{"name": "query", "arguments": ""}]', "content": ""})
    sig = engine.update({"role": "environment", "thought": "", "action": "", "content": "Fatal: Database crashed"})

    judge = LLMJudge(client=MockLLMClient())
    resp = judge.judge_step(
        task_prompt="Run query",
        turns_prefix=engine.history,
        signals=sig,
        ml_risk_prob=0.75,
    )

    assert isinstance(resp, JudgeResponse)
    assert resp.verdict == JudgeVerdict.ALARM
    assert resp.reason_category in (ReasonCategory.TOOL_FAILURE, ReasonCategory.LOOP, ReasonCategory.PLAN_MISMATCH)


def test_judge_graceful_fallback_on_network_error():
    """Confirms system does not crash when LLM network fails."""
    engine = RuntimeSignalsEngine(task_prompt="Test")
    sig = engine.update({"role": "user", "thought": "", "action": "", "content": "Hello"})

    judge = LLMJudge(client=FaultyLLMClient())
    resp = judge.judge_step(
        task_prompt="Test",
        turns_prefix=[{"role": "user", "content": "Hello"}],
        signals=sig,
        ml_risk_prob=0.80,  # High ML risk triggers fallback ALARM
    )

    assert isinstance(resp, JudgeResponse)
    assert resp.verdict == JudgeVerdict.ALARM
    assert resp.reason_category == ReasonCategory.UNKNOWN
    assert resp.confidence_level == JudgeConfidence.LOW
    assert "fallback" in resp.explanation.lower()


def test_judge_graceful_fallback_on_malformed_json():
    engine = RuntimeSignalsEngine(task_prompt="Test")
    sig = engine.update({"role": "user", "thought": "", "action": "", "content": "Hello"})

    judge = LLMJudge(client=MalformedJSONClient())
    resp = judge.judge_step(
        task_prompt="Test",
        turns_prefix=[{"role": "user", "content": "Hello"}],
        signals=sig,
        ml_risk_prob=0.20,  # Low ML risk triggers fallback CONTINUE
    )

    assert isinstance(resp, JudgeResponse)
    assert resp.verdict == JudgeVerdict.CONTINUE
    assert resp.reason_category == ReasonCategory.UNKNOWN

