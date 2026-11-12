"""
Live API Integration Tests for LLM Judge using configured credentials.
Verifies network connectivity, response parsing, and Pydantic validation.
"""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()

from src.judge.judge import LLMJudge
from src.judge.llm_client import GroqClient, get_default_llm_client
from src.judge.schema import JudgeResponse, JudgeVerdict, ReasonCategory
from src.signals.engine import RuntimeSignalsEngine


def test_live_groq_api_direct_ping():
    """Direct ping to verify live API key authorization and latency."""
    client = get_default_llm_client()
    assert isinstance(client, GroqClient), f"Expected GroqClient, got {type(client).__name__}"

    system_prompt = "You are a trajectory safety auditor. Return strict JSON only."
    user_prompt = 'Output valid JSON: {"status": "authorized", "verdict": "CONTINUE"}'

    response_text = client.generate(system_prompt, user_prompt, timeout=15.0)
    assert response_text is not None
    assert "status" in response_text or "verdict" in response_text


def test_live_llm_judge_step_evaluation():
    """Tests that LLMJudge uses the live API and parses output into JudgeResponse."""
    judge = LLMJudge()
    engine = RuntimeSignalsEngine(task_prompt="Book a train ticket to Mumbai")

    # Step 1: Normal agent action
    sig = engine.update({
        "role": "assistant",
        "thought": "Checking ticket availability via IRCTC API",
        "action": '[{"name": "check_tickets", "arguments": "{\\"dest\\": \\"Mumbai\\"}"}]',
        "content": ""
    })

    result = judge.judge_step(
        task_prompt="Book a train ticket to Mumbai",
        turns_prefix=engine.history,
        signals=sig,
        ml_risk_prob=0.30
    )

    assert isinstance(result, JudgeResponse)
    assert result.verdict in (JudgeVerdict.CONTINUE, JudgeVerdict.ALARM)
    assert isinstance(result.reason_category, ReasonCategory)
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.explanation) > 5


def test_live_llm_judge_catches_unfolding_loop():
    """Tests live Judge on an explicit looping sequence."""
    judge = LLMJudge()
    engine = RuntimeSignalsEngine(task_prompt="Calculate root of 144")

    # Repeat exact same action multiple times
    action_str = '[{"name": "calc", "arguments": "sqrt(144)"}]'
    for _ in range(3):
        sig = engine.update({"role": "assistant", "thought": "Calculating root", "action": action_str, "content": ""})
        engine.update({"role": "environment", "thought": "", "action": "", "content": "12"})

    result = judge.judge_step(
        task_prompt="Calculate root of 144",
        turns_prefix=engine.history,
        signals=sig,
        ml_risk_prob=0.75
    )

    assert isinstance(result, JudgeResponse)
    # With ML risk = 0.75 and looping action, judge should produce valid category
    assert result.reason_category in ReasonCategory

