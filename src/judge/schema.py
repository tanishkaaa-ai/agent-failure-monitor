"""
Pydantic Schemas for LLM Judge.
Validates structured output from the LLM Judge before passing to downstream modules.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class JudgeVerdict(str, Enum):
    CONTINUE = "CONTINUE"
    ALARM = "ALARM"


class ReasonCategory(str, Enum):
    TOOL_FAILURE = "TOOL_FAILURE"
    TEMPORARY_TIMEOUT = "TEMPORARY_TIMEOUT"
    LOOP = "LOOP"
    PLAN_MISMATCH = "PLAN_MISMATCH"
    STAGNATION = "STAGNATION"
    UNKNOWN = "UNKNOWN"


class JudgeConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class JudgeResponse(BaseModel):
    """
    Validated response from the prompted LLM Judge.
    Strictly diagnostic; does not plan interventions.
    """
    verdict: JudgeVerdict = Field(
        ...,
        description="Auditing verdict: CONTINUE (trajectory safe to proceed) or ALARM (failure detected/imminent)."
    )
    reason_category: ReasonCategory = Field(
        ...,
        description="Categorical reason for the verdict."
    )
    explanation: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Concise natural-language explanation of the current trajectory state."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Numerical confidence in the verdict between 0.0 and 1.0."
    )
    confidence_level: JudgeConfidence = Field(
        default=JudgeConfidence.MEDIUM,
        description="Categorical confidence level: LOW, MEDIUM, or HIGH."
    )
    raw_response: Optional[str] = Field(
        default=None,
        description="Raw text returned by the LLM (for debugging and audit logs)."
    )

    @field_validator("confidence_level", mode="before")
    @classmethod
    def infer_confidence_level(cls, v, values):
        if isinstance(v, JudgeConfidence):
            return v
        if isinstance(v, str) and v.upper() in JudgeConfidence.__members__:
            return JudgeConfidence[v.upper()]
        return JudgeConfidence.MEDIUM

