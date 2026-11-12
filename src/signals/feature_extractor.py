"""
Runtime Signal and Feature Extractor for Online Agent Trajectory Auditing.
Extracts step-level features using strictly historical information up to step t.
No future information is leaked.
"""

import json
import re
from typing import Any, Dict, List, Optional, Set

ERROR_KEYWORDS = [
    "error", "exception", "traceback", "failed", "syntaxerror",
    "nameerror", "typeerror", "zerodivisionerror", "timeout",
    "field required", "validation error", "assertionerror", "runtimeerror"
]


def tokenize_text(text: str) -> Set[str]:
    """Tokenize text into lowercase alphanumeric words."""
    if not text:
        return set()
    return set(re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower()))


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity between two token sets."""
    if not set_a and not set_b:
        return 0.0
    union = set_a.union(set_b)
    if not union:
        return 0.0
    return len(set_a.intersection(set_b)) / len(union)


def parse_action_tools(action_str: str) -> List[str]:
    """Parse tool names from the action JSON string if present."""
    if not action_str or not action_str.strip():
        return []
    try:
        data = json.loads(action_str)
        if isinstance(data, list):
            tools = [item.get("name", "unknown") for item in data if isinstance(item, dict)]
            return tools
        elif isinstance(data, dict):
            return [data.get("name", "unknown")]
    except Exception:
        # Fallback regex search for "name": "tool_name"
        matches = re.findall(r'["\']name["\']\s*:\s*["\']([^"\']+)["\']', action_str)
        if matches:
            return matches
    return ["generic_action"]


def is_environment_error(content: str) -> bool:
    """Detect if an environment turn indicates a tool execution failure."""
    if not content:
        return False
    lower_c = content.lower()
    return any(kw in lower_c for kw in ERROR_KEYWORDS)


def extract_step_features(
    conv_id: str,
    domain: str,
    task_text: str,
    turns: List[Dict[str, Any]],
    step_idx: int,
    mistake_step: int = -1,
    mistake_agent: str = "",
    unsafe_source: str = "safe",
    split: str = "train",
) -> Dict[str, Any]:
    """
    Extract runtime features for the partial trajectory up to step_idx (0 <= t <= step_idx).
    Guarantees zero data leakage from turns > step_idx.
    """
    current_turn = turns[step_idx]
    current_role = str(current_turn.get("role", "unknown"))
    current_thought = str(current_turn.get("thought", "") or "")
    current_action = str(current_turn.get("action", "") or "")
    current_content = str(current_turn.get("content", "") or "")

    # 1. Structural / Positional signals
    is_agent_turn = int(current_role not in ("user", "environment"))
    is_env_turn = int(current_role == "environment")
    is_user_turn = int(current_role == "user")

    # 2. Step text lengths
    thought_len_chars = len(current_thought)
    thought_len_words = len(current_thought.split())
    content_len_chars = len(current_content)
    content_len_words = len(current_content.split())
    action_len_chars = len(current_action)

    # 3. Action and Tool details in current step
    current_tools = parse_action_tools(current_action)
    num_tools_in_step = len(current_tools)
    has_action = int(bool(current_action.strip()))

    # 4. History accumulation up to step_idx (Strictly t <= step_idx)
    cum_agent_turns = 0
    cum_env_turns = 0
    cum_user_turns = 0
    cum_tool_calls = 0
    unique_tools: Set[str] = set()
    cum_tool_errors = 0
    consecutive_tool_errors = 0
    action_history: List[str] = []
    all_accumulated_words: List[str] = []

    last_role = None
    consecutive_role_turns = 0

    for i in range(step_idx + 1):
        t = turns[i]
        r = str(t.get("role", ""))
        th = str(t.get("thought", "") or "")
        act = str(t.get("action", "") or "")
        cnt = str(t.get("content", "") or "")

        if r in ("user",):
            cum_user_turns += 1
        elif r in ("environment",):
            cum_env_turns += 1
            if is_environment_error(cnt):
                cum_tool_errors += 1
                consecutive_tool_errors += 1
            else:
                consecutive_tool_errors = 0
        else:
            cum_agent_turns += 1

        tools_called = parse_action_tools(act)
        cum_tool_calls += len(tools_called)
        unique_tools.update(tools_called)

        if act.strip():
            action_history.append(act.strip())

        if r == last_role:
            consecutive_role_turns += 1
        else:
            last_role = r
            consecutive_role_turns = 1

        # Token tracking for lexical diversity and drift
        if r != "user":
            all_accumulated_words.extend((th + " " + cnt).lower().split())

    # Rates
    tool_failure_rate = (
        cum_tool_errors / max(1, cum_env_turns) if cum_env_turns > 0 else 0.0
    )
    agent_env_turn_ratio = (
        cum_agent_turns / max(1, cum_env_turns) if cum_env_turns > 0 else float(cum_agent_turns)
    )

    # 5. Repetition and Loops
    action_repeat_count = 0
    if current_action.strip() and len(action_history) > 1:
        # Number of times current action was seen strictly before this turn
        action_repeat_count = action_history[:-1].count(current_action.strip())

    consecutive_same_action = 0
    if len(action_history) >= 2 and action_history[-1] == action_history[-2]:
        consecutive_same_action = 1

    # Inter-turn token similarity (turn t vs turn t-1)
    content_jaccard_prev = 0.0
    thought_jaccard_prev = 0.0
    if step_idx > 0:
        prev_t = turns[step_idx - 1]
        prev_cnt = str(prev_t.get("content", "") or "")
        prev_th = str(prev_t.get("thought", "") or "")
        content_jaccard_prev = jaccard_similarity(
            tokenize_text(current_content), tokenize_text(prev_cnt)
        )
        thought_jaccard_prev = jaccard_similarity(
            tokenize_text(current_thought), tokenize_text(prev_th)
        )

    # 6. Stagnation Score over last 3 turns
    window_start = max(0, step_idx - 2)
    window_turns = turns[window_start : step_idx + 1]
    stagnant_turns = 0
    window_words: List[str] = []

    for w_turn in window_turns:
        w_th = str(w_turn.get("thought", "") or "").strip()
        w_cnt = str(w_turn.get("content", "") or "").strip()
        w_act = str(w_turn.get("action", "") or "").strip()
        # Stagnant if no reasoning, no content, and no action
        if not w_th and not w_cnt and not w_act:
            stagnant_turns += 1
        window_words.extend((w_th + " " + w_cnt).lower().split())

    stagnation_score_3 = stagnant_turns / len(window_turns)
    unique_window_words = set(window_words)
    lexical_diversity_3 = (
        len(unique_window_words) / max(1, len(window_words)) if window_words else 1.0
    )

    # 7. Task Alignment / Drift (Proxy for Plan Mismatch)
    task_tokens = tokenize_text(task_text)
    task_word_count = len(task_text.split())
    current_tokens = tokenize_text(current_thought + " " + current_content)
    task_token_overlap = jaccard_similarity(current_tokens, task_tokens)

    accumulated_tokens = set(all_accumulated_words)
    cum_task_token_overlap = jaccard_similarity(accumulated_tokens, task_tokens)

    # 8. Target Labeling & Failure Supervision
    mistake_agent = mistake_agent if (mistake_agent and mistake_agent.strip()) else "none"
    is_unsafe_traj = int(mistake_step >= 0)
    is_mistake_step = int(is_unsafe_traj and step_idx == mistake_step)
    post_failure = int(is_unsafe_traj and step_idx > mistake_step)
    steps_to_failure = (mistake_step - step_idx) if is_unsafe_traj else -1

    # Primary Target: Will this unfolding trajectory fail in the future / at this step?
    # For safe trajectories: 0
    # For unsafe trajectories: 1 for all steps prior to and including mistake_step
    will_fail = int(is_unsafe_traj and step_idx <= mistake_step)

    # Horizon Targets: Imminent failure within 3 or 5 steps
    fail_within_3_steps = int(is_unsafe_traj and 0 <= steps_to_failure <= 3)
    fail_within_5_steps = int(is_unsafe_traj and 0 <= steps_to_failure <= 5)

    return {
        "conv_id": conv_id,
        "split": split,
        "domain": domain,
        "step_idx": step_idx,
        "current_role": current_role,
        "is_agent_turn": is_agent_turn,
        "is_env_turn": is_env_turn,
        "is_user_turn": is_user_turn,
        "has_action": has_action,
        "num_tools_in_step": num_tools_in_step,
        "action_len_chars": action_len_chars,
        "thought_len_chars": thought_len_chars,
        "thought_len_words": thought_len_words,
        "content_len_chars": content_len_chars,
        "content_len_words": content_len_words,
        "cum_agent_turns": cum_agent_turns,
        "cum_env_turns": cum_env_turns,
        "cum_tool_calls": cum_tool_calls,
        "unique_tools_used": len(unique_tools),
        "cum_tool_errors": cum_tool_errors,
        "consecutive_tool_errors": consecutive_tool_errors,
        "tool_failure_rate": round(tool_failure_rate, 4),
        "agent_env_turn_ratio": round(agent_env_turn_ratio, 4),
        "action_repeat_count": action_repeat_count,
        "consecutive_same_action": consecutive_same_action,
        "consecutive_role_turns": consecutive_role_turns,
        "content_jaccard_prev": round(content_jaccard_prev, 4),
        "thought_jaccard_prev": round(thought_jaccard_prev, 4),
        "stagnation_score_3": round(stagnation_score_3, 4),
        "lexical_diversity_3": round(lexical_diversity_3, 4),
        "task_word_count": task_word_count,
        "task_token_overlap": round(task_token_overlap, 4),
        "cum_task_token_overlap": round(cum_task_token_overlap, 4),
        # Failure Labels & Metadata
        "mistake_step": mistake_step,
        "mistake_agent": mistake_agent,
        "unsafe_source": unsafe_source,
        "is_unsafe_traj": is_unsafe_traj,
        "post_failure": post_failure,
        "is_mistake_step": is_mistake_step,
        "steps_to_failure": steps_to_failure,
        "fail_within_3_steps": fail_within_3_steps,
        "fail_within_5_steps": fail_within_5_steps,
        "will_fail": will_fail,
    }
