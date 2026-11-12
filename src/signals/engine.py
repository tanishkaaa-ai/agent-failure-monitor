"""
Phase 4: Runtime Signals Engine
A rule-based component that computes online runtime signals after every agent execution step.
Supports both stateful streaming (for live agent interception) and batch prefix evaluation.
Operates strictly on historical information available up to the current turn (zero future leakage).
"""

from dataclasses import asdict, dataclass
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

ERROR_KEYWORDS = [
    "error", "exception", "traceback", "failed", "syntaxerror",
    "nameerror", "typeerror", "zerodivisionerror", "timeout",
    "field required", "validation error", "assertionerror", "runtimeerror"
]


def tokenize(text: str) -> Set[str]:
    """Tokenize lowercase alphanumeric words."""
    if not text:
        return set()
    return set(re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower()))


def jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity between two token sets."""
    if not set_a and not set_b:
        return 0.0
    union = set_a.union(set_b)
    if not union:
        return 0.0
    return len(set_a.intersection(set_b)) / len(union)


def parse_tools_from_action(action_str: str) -> List[Tuple[str, str]]:
    """
    Parse (tool_name, arguments_str) pairs from action string.
    Returns empty list if no tool calls exist.
    """
    if not action_str or not action_str.strip():
        return []
    results = []
    try:
        data = json.loads(action_str)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    name = str(item.get("name", "unknown"))
                    args = str(item.get("arguments", ""))
                    results.append((name, args))
        elif isinstance(data, dict):
            name = str(data.get("name", "unknown"))
            args = str(data.get("arguments", ""))
            results.append((name, args))
    except Exception:
        matches = re.findall(r'["\']name["\']\s*:\s*["\']([^"\']+)["\']', action_str)
        for m in matches:
            results.append((m, ""))
    return results


def is_error_response(content: str) -> bool:
    """Check if environment output indicates tool failure."""
    if not content:
        return False
    lower_c = content.lower()
    return any(kw in lower_c for kw in ERROR_KEYWORDS)


@dataclass
class SignalVector:
    """
    Structured representation of runtime signals computed at step t.
    All numerical features can be converted to dict, numpy array, or pandas DataFrame.
    """
    step_idx: int
    role: str
    is_agent_turn: int
    is_env_turn: int

    # 1. Retry signals
    active_retry_count: int          # Retries on the currently failing tool
    cumulative_retries: int          # Total retries across the trajectory
    is_retry_step: int               # 1 if current step is actively re-invoking a failed tool
    isolated_failure_flag: int       # 1 if only an isolated failure occurred with 0 retries

    # 2. Tool failure signals
    tool_failure_rate: float         # cum_tool_errors / max(1, cum_env_turns)
    consecutive_tool_failures: int   # Current uninterrupted streak of environment errors
    cum_tool_calls: int              # Total tool calls dispatched so far
    cum_tool_errors: int             # Total environment errors encountered

    # 3. Repeated action & loop signals
    action_repetition_count: int     # Prior occurrences of exact current action
    consecutive_same_action: int     # 1 if current action is identical to previous non-empty action
    content_repetition_score: float  # Jaccard similarity between current content and previous content
    loop_indicator_score: float      # Composite loop score in [0.0, 1.0]

    # 4. Stagnation & progress signals
    stagnation_score: float          # Ratio of zero-progress turns in recent window (window=3)
    lexical_diversity: float         # Type-token ratio of words in recent turns
    cum_thought_words: int           # Cumulative reasoning words
    reasoning_explosion_ratio: float # Ratio of current thought length to rolling average thought length

    # 5. Plan-execution mismatch / Task drift
    plan_mismatch_score: float       # 1.0 - task_token_overlap (drift of current turn from task)
    cum_task_drift_score: float      # 1.0 - cum_task_token_overlap (drift of all history from task)

    # 6. Action diversity
    action_diversity: float          # unique_tools / max(1, cum_tool_calls)

    # 7. Monologue & Communication patterns
    consecutive_agent_monologue: int # Consecutive agent turns without environment feedback

    # Composite rule-based risk indicator (Heuristic pre-ML baseline)
    rule_risk_score: float           # Weighted heuristic score in [0.0, 1.0]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_features_dict(self) -> Dict[str, float]:
        """Returns numerical feature dictionary suitable for ML models."""
        d = self.to_dict()
        # Exclude non-numeric metadata
        del d["role"]
        return {k: float(v) for k, v in d.items()}

    def to_numpy(self) -> np.ndarray:
        """Returns numerical feature vector."""
        return np.array(list(self.to_features_dict().values()), dtype=np.float32)

    @classmethod
    def feature_names(cls) -> List[str]:
        """Returns list of numerical feature names."""
        sample = cls(
            step_idx=0, role="", is_agent_turn=0, is_env_turn=0,
            active_retry_count=0, cumulative_retries=0, is_retry_step=0, isolated_failure_flag=0,
            tool_failure_rate=0.0, consecutive_tool_failures=0, cum_tool_calls=0, cum_tool_errors=0,
            action_repetition_count=0, consecutive_same_action=0, content_repetition_score=0.0,
            loop_indicator_score=0.0, stagnation_score=0.0, lexical_diversity=1.0,
            cum_thought_words=0, reasoning_explosion_ratio=1.0,
            plan_mismatch_score=0.0, cum_task_drift_score=0.0,
            action_diversity=1.0, consecutive_agent_monologue=0, rule_risk_score=0.0
        )
        return list(sample.to_features_dict().keys())


class RuntimeSignalsEngine:
    """
    Stateful Runtime Signals Engine.
    Monitors an unfolding agent trajectory turn-by-turn and extracts calibrated signals.
    """

    def __init__(self, task_prompt: str = ""):
        self.task_prompt = task_prompt or ""
        self.task_tokens = tokenize(self.task_prompt)
        self.reset()

    def reset(self, task_prompt: Optional[str] = None) -> None:
        """Reset internal trajectory state."""
        if task_prompt is not None:
            self.task_prompt = task_prompt
            self.task_tokens = tokenize(self.task_prompt)

        self.history: List[Dict[str, Any]] = []
        self.signal_history: List[SignalVector] = []

        # Tool tracking & Retry state machine
        self.cum_tool_calls: int = 0
        self.unique_tools: Set[str] = set()
        self.cum_env_turns: int = 0
        self.cum_tool_errors: int = 0
        self.consecutive_tool_failures: int = 0

        # Retry tracking state
        self.last_attempted_tool: Optional[str] = None
        self.last_attempted_args: Optional[str] = None
        self.pending_tool_failure: bool = False
        self.failing_tool_name: Optional[str] = None
        self.active_retry_count: int = 0
        self.cumulative_retries: int = 0

        # Action history
        self.action_history: List[str] = []

        # Text accumulation
        self.all_generated_words: List[str] = []
        self.thought_word_lengths: List[int] = []
        self.cum_thought_words: int = 0

        # Communication streaks
        self.consecutive_monologue: int = 0

    def update(self, turn: Dict[str, Any]) -> SignalVector:
        """
        Process a single new turn in the unfolding trajectory and return updated SignalVector.
        Operates strictly on current turn and accumulated history.
        """
        step_idx = len(self.history)
        self.history.append(turn)

        role = str(turn.get("role", "unknown"))
        thought = str(turn.get("thought", "") or "")
        action = str(turn.get("action", "") or "")
        content = str(turn.get("content", "") or "")

        # 1. Role identification & streaks
        is_agent_turn = int(role not in ("user", "environment"))
        is_env_turn = int(role == "environment")

        if is_agent_turn:
            self.consecutive_monologue += 1
        elif is_env_turn:
            self.consecutive_monologue = 0
        else:
            self.consecutive_monologue = 0

        # 2. Text metrics
        thought_words = thought.split()
        content_words = content.split()
        th_word_count = len(thought_words)
        self.thought_word_lengths.append(th_word_count)
        self.cum_thought_words += th_word_count

        if role != "user":
            self.all_generated_words.extend((thought + " " + content).lower().split())

        # Reasoning explosion
        if len(self.thought_word_lengths) > 1:
            prev_avg = np.mean(self.thought_word_lengths[:-1])
            reasoning_explosion = float(th_word_count / max(1.0, prev_avg))
        else:
            reasoning_explosion = 1.0

        # 3. Action and Tool Parsing
        tools_called = parse_tools_from_action(action)
        is_retry_step = 0

        if tools_called:
            self.cum_tool_calls += len(tools_called)
            primary_tool_name, primary_tool_args = tools_called[0]
            self.unique_tools.add(primary_tool_name)

            # Check if this action is an active retry following a previous tool failure
            if self.pending_tool_failure and self.failing_tool_name == primary_tool_name:
                self.active_retry_count += 1
                self.cumulative_retries += 1
                is_retry_step = 1
            elif self.pending_tool_failure and self.failing_tool_name != primary_tool_name:
                # Agent decided not to retry the failing tool, but switched tools
                self.pending_tool_failure = False
                self.active_retry_count = 0

            self.last_attempted_tool = primary_tool_name
            self.last_attempted_args = primary_tool_args

        # 4. Environment Feedback & Tool Failure Handling
        if is_env_turn:
            self.cum_env_turns += 1
            if is_error_response(content):
                self.cum_tool_errors += 1
                self.consecutive_tool_failures += 1
                # Mark tool as failing; note: retry_count does NOT increment until agent retries
                self.pending_tool_failure = True
                self.failing_tool_name = self.last_attempted_tool
            else:
                # Successful execution resets the pending failure and retry streak
                self.consecutive_tool_failures = 0
                self.pending_tool_failure = False
                self.failing_tool_name = None
                self.active_retry_count = 0

        # Isolated failure: exactly 1 error occurred, but 0 retries triggered yet
        isolated_failure_flag = int(self.cum_tool_errors == 1 and self.cumulative_retries == 0)

        # Failure rates
        tool_failure_rate = (
            float(self.cum_tool_errors / max(1, self.cum_env_turns))
            if self.cum_env_turns > 0
            else 0.0
        )

        # 5. Repetition and Loops
        action_repetition_count = 0
        consecutive_same_action = 0
        clean_action = action.strip()

        if clean_action:
            if clean_action in self.action_history:
                action_repetition_count = self.action_history.count(clean_action)
            if self.action_history and self.action_history[-1] == clean_action:
                consecutive_same_action = 1
            self.action_history.append(clean_action)

        # Content repetition (turn t vs turn t-1)
        content_repetition_score = 0.0
        if step_idx > 0:
            prev_content = str(self.history[-2].get("content", "") or "")
            content_repetition_score = jaccard(tokenize(content), tokenize(prev_content))

        # Composite Loop Score [0, 1]
        loop_score_components = [
            min(1.0, action_repetition_count * 0.4),
            float(consecutive_same_action) * 0.5,
            content_repetition_score * 0.3,
        ]
        loop_indicator_score = min(1.0, sum(loop_score_components))

        # 6. Stagnation & Lexical Diversity (sliding window = 3)
        window = self.history[-3:]
        stagnant_count = 0
        window_words: List[str] = []
        for w in window:
            w_th = str(w.get("thought", "") or "").strip()
            w_cnt = str(w.get("content", "") or "").strip()
            w_act = str(w.get("action", "") or "").strip()
            if not w_th and not w_cnt and not w_act:
                stagnant_count += 1
            window_words.extend((w_th + " " + w_cnt).lower().split())

        stagnation_score = float(stagnant_count / len(window))
        unique_w = set(window_words)
        lexical_diversity = float(len(unique_w) / max(1, len(window_words))) if window_words else 1.0

        # 7. Plan Mismatch / Task Drift (lexical ground truth)
        turn_tokens = tokenize(thought + " " + content)
        task_overlap = jaccard(turn_tokens, self.task_tokens)
        plan_mismatch_score = float(1.0 - task_overlap)

        cum_tokens = set(self.all_generated_words)
        cum_task_overlap = jaccard(cum_tokens, self.task_tokens)
        cum_task_drift_score = float(1.0 - cum_task_overlap)

        # 8. Action Diversity
        if self.cum_tool_calls > 0:
            action_diversity = float(len(self.unique_tools) / self.cum_tool_calls)
        else:
            action_diversity = 1.0

        # 9. Composite Rule-Based Risk Heuristic
        # Balances retries, consecutive errors, looping, and stagnation
        # Isolated failures (1 error, 0 retries) do not spike this score
        risk_penalties = [
            min(1.0, self.active_retry_count * 0.35),          # High retries = high risk
            min(1.0, self.consecutive_tool_failures * 0.30),   # Repeated crashes = high risk
            loop_indicator_score * 0.25,                       # Loops = high risk
            stagnation_score * 0.20,                           # Stagnation = moderate risk
            max(0.0, (1.0 - action_diversity)) * 0.15 if self.cum_tool_calls >= 3 else 0.0,
            0.15 if self.consecutive_monologue >= 4 else 0.0, # Unchecked monologue = risk
        ]
        # Mitigate if it's strictly an isolated first failure
        raw_risk = sum(risk_penalties)
        if isolated_failure_flag:
            raw_risk = min(raw_risk, 0.25)
        rule_risk_score = round(min(1.0, max(0.0, raw_risk)), 4)

        sig = SignalVector(
            step_idx=step_idx,
            role=role,
            is_agent_turn=is_agent_turn,
            is_env_turn=is_env_turn,
            active_retry_count=self.active_retry_count,
            cumulative_retries=self.cumulative_retries,
            is_retry_step=is_retry_step,
            isolated_failure_flag=isolated_failure_flag,
            tool_failure_rate=round(tool_failure_rate, 4),
            consecutive_tool_failures=self.consecutive_tool_failures,
            cum_tool_calls=self.cum_tool_calls,
            cum_tool_errors=self.cum_tool_errors,
            action_repetition_count=action_repetition_count,
            consecutive_same_action=consecutive_same_action,
            content_repetition_score=round(content_repetition_score, 4),
            loop_indicator_score=round(loop_indicator_score, 4),
            stagnation_score=round(stagnation_score, 4),
            lexical_diversity=round(lexical_diversity, 4),
            cum_thought_words=self.cum_thought_words,
            reasoning_explosion_ratio=round(min(10.0, reasoning_explosion), 4),
            plan_mismatch_score=round(plan_mismatch_score, 4),
            cum_task_drift_score=round(cum_task_drift_score, 4),
            action_diversity=round(action_diversity, 4),
            consecutive_agent_monologue=self.consecutive_monologue,
            rule_risk_score=rule_risk_score,
        )

        self.signal_history.append(sig)
        return sig

    def evaluate_prefix(
        self, turns: List[Dict[str, Any]], task_prompt: Optional[str] = None
    ) -> List[SignalVector]:
        """
        Evaluate an entire trajectory or prefix from scratch step-by-step.
        Guarantees exact parity with live streaming mode.
        """
        self.reset(task_prompt=task_prompt)
        results = []
        for turn in turns:
            results.append(self.update(turn))
        return results

