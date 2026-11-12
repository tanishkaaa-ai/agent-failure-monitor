"""
LLM Judge for Real-Time Agent Trajectory Safety Auditing.
Analyzes unfolding trajectory prefixes, runtime signals, and ML failure risk
to produce a validated structured verdict and categorical diagnosis.

Note: This is a prompted LLM reasoning component (not RL-trained).
It performs trajectory auditing only and is kept strictly separate from
intervention selection.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.judge.llm_client import BaseLLMClient, get_default_llm_client
from src.judge.prompt import JUDGE_SYSTEM_PROMPT, format_judge_user_prompt
from src.judge.schema import (
    JudgeConfidence,
    JudgeResponse,
    JudgeVerdict,
    ReasonCategory,
)
from src.signals.engine import SignalVector

logger = logging.getLogger(__name__)


def clean_json_text(text: str) -> str:
    """Extract clean JSON substring from potential markdown wrappers."""
    text = text.strip()
    # Strip markdown code blocks ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


class LLMJudge:
    """
    Prompted LLM Judge for trajectory auditing and failure verification.
    """

    def __init__(self, client: Optional[BaseLLMClient] = None):
        self.client = client or get_default_llm_client()

    def judge_step(
        self,
        task_prompt: str,
        turns_prefix: List[Dict[str, Any]],
        signals: SignalVector,
        ml_risk_prob: float,
    ) -> JudgeResponse:
        """
        Audit the current trajectory step and return a validated JudgeResponse.

        Parameters
        ----------
        task_prompt : str
            The original task description given to the agent.
        turns_prefix : list[dict]
            Execution history up to the current turn.
        signals : SignalVector
            Calculated runtime metrics from the Signals Engine.
        ml_risk_prob : float
            Predicted probability of future failure from the ML classifier.

        Returns
        -------
        JudgeResponse
            Pydantic-validated verdict, category, explanation, and confidence.
        """
        user_prompt = format_judge_user_prompt(
            task_prompt=task_prompt,
            turns_prefix=turns_prefix,
            signals=signals,
            ml_risk_prob=ml_risk_prob,
        )

        try:
            raw_text = self.client.generate(
                system_prompt=JUDGE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            cleaned_text = clean_json_text(raw_text)
            parsed_data = json.loads(cleaned_text)

            # Validate via Pydantic
            response = JudgeResponse(
                verdict=JudgeVerdict(parsed_data["verdict"].upper()),
                reason_category=ReasonCategory(parsed_data["reason_category"].upper()),
                explanation=str(parsed_data["explanation"]).strip(),
                confidence=float(parsed_data.get("confidence", 0.7)),
                confidence_level=JudgeConfidence(
                    str(parsed_data.get("confidence_level", "MEDIUM")).upper()
                ),
                raw_response=raw_text,
            )
            return response

        except Exception as e:
            logger.warning(f"LLM Judge call or parsing failed: {e}. Falling back to safe default.")
            # Graceful degradation fallback
            fallback_verdict = (
                JudgeVerdict.ALARM if ml_risk_prob >= 0.60 else JudgeVerdict.CONTINUE
            )
            return JudgeResponse(
                verdict=fallback_verdict,
                reason_category=ReasonCategory.UNKNOWN,
                explanation=f"Auditor fallback (LLM response unavailable or invalid: {type(e).__name__}).",
                confidence=0.50,
                confidence_level=JudgeConfidence.LOW,
                raw_response=None,
            )

