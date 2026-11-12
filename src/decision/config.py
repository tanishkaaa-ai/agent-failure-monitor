"""
Configurable Thresholds and Parameters for the Decision System.
"""

from dataclasses import dataclass
import os
from typing import Any, Dict, Optional
import yaml


@dataclass
class DecisionConfig:
    """Configurable parameters governing multi-signal decision fusion."""

    # ML Classifier Thresholds
    ml_alarm_threshold: float = 0.60
    ml_continue_threshold: float = 0.35
    ml_override_threshold: float = 0.85

    # Critical Runtime Signal Override Thresholds
    max_retries_threshold: int = 3
    max_consecutive_failures: int = 3
    critical_loop_threshold: float = 0.85
    critical_stagnation_threshold: float = 0.90

    # LLM Judge Thresholds
    llm_high_confidence: float = 0.75
    llm_low_confidence: float = 0.50

    # Logging
    log_decisions: bool = True

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "DecisionConfig":
        """Load configuration from a YAML file."""
        if not os.path.exists(yaml_path):
            return cls()
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        thresh = data.get("thresholds", {})
        logging_cfg = data.get("logging", {})

        return cls(
            ml_alarm_threshold=float(thresh.get("ml_alarm_threshold", 0.60)),
            ml_continue_threshold=float(thresh.get("ml_continue_threshold", 0.35)),
            ml_override_threshold=float(thresh.get("ml_override_threshold", 0.85)),
            max_retries_threshold=int(thresh.get("max_retries_threshold", 3)),
            max_consecutive_failures=int(thresh.get("max_consecutive_failures", 3)),
            critical_loop_threshold=float(thresh.get("critical_loop_threshold", 0.85)),
            critical_stagnation_threshold=float(thresh.get("critical_stagnation_threshold", 0.90)),
            llm_high_confidence=float(thresh.get("llm_high_confidence", 0.75)),
            llm_low_confidence=float(thresh.get("llm_low_confidence", 0.50)),
            log_decisions=bool(logging_cfg.get("enabled", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ml_alarm_threshold": self.ml_alarm_threshold,
            "ml_continue_threshold": self.ml_continue_threshold,
            "ml_override_threshold": self.ml_override_threshold,
            "max_retries_threshold": self.max_retries_threshold,
            "max_consecutive_failures": self.max_consecutive_failures,
            "critical_loop_threshold": self.critical_loop_threshold,
            "critical_stagnation_threshold": self.critical_stagnation_threshold,
            "llm_high_confidence": self.llm_high_confidence,
            "llm_low_confidence": self.llm_low_confidence,
            "log_decisions": self.log_decisions,
        }

