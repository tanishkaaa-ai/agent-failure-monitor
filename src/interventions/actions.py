"""
Action Types, Plans, and Outcomes for the Intervention Layer.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class InterventionActionType(str, Enum):
    RETRY_WITH_BACKOFF = "RETRY_WITH_BACKOFF"
    SWITCH_TOOL = "SWITCH_TOOL"
    BREAK_LOOP_AND_REPLAN = "BREAK_LOOP_AND_REPLAN"
    REPLAN = "REPLAN"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    TERMINATE = "TERMINATE"


@dataclass
class InterventionPlan:
    """Selected single recovery action plan to resolve an ALARM."""
    action_type: InterventionActionType
    target_tool: Optional[str] = None
    fallback_tool: Optional[str] = None
    backoff_seconds: float = 0.0
    prompt_injection: Optional[str] = None
    rationale: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        return d


@dataclass
class InterventionOutcome:
    """Audit record capturing the executed intervention and its result."""
    step_idx: int
    decision_reason_category: str
    action_type: InterventionActionType
    status: str  # "APPLIED", "ESCALATED", "TERMINATED", "FAILED"
    details: str
    injected_message: Optional[Dict[str, Any]] = None  # Synthetic feedback turn for the agent
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        return d

