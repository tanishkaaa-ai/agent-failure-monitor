"""
Prompt templates and formatting utilities for the LLM Judge.
Provides structured prompt engineering for trajectory auditing.
"""

import json
from typing import Any, Dict, List, Optional
from src.signals.engine import SignalVector

JUDGE_SYSTEM_PROMPT = """You are an impartial, real-time AI Agent Trajectory Auditor and Safety Judge.
Your task is to monitor an AI agent's partial execution trajectory turn-by-turn, analyze runtime signals, consider a lightweight ML model's predicted failure-risk probability, and return an auditing verdict.

You must choose one of two verdicts:
1. CONTINUE: The agent is executing productively, recovering from a minor transient issue, or working toward the goal.
2. ALARM: The agent has suffered an unrecovered decisive failure, is trapped in an infinite loop, repeating broken tool calls, stagnating, or drifting severely off-task.

You must classify the diagnosis into exactly one of these reason categories:
- TOOL_FAILURE: Unrecoverable tool crash, invalid arguments, or repeated tool errors.
- TEMPORARY_TIMEOUT: Transient glitch or network delay that is likely recoverable.
- LOOP: Cyclic repetition of identical actions, thoughts, or responses.
- PLAN_MISMATCH: The agent is pursuing an irrelevant task or hallucinating requirements.
- STAGNATION: The agent is not making forward progress (empty turns, rambling).
- UNKNOWN: Insufficient evidence or normal ongoing progress.

Your response MUST be a single valid JSON object with these exact keys:
{
  "verdict": "CONTINUE" or "ALARM",
  "reason_category": "TOOL_FAILURE" | "TEMPORARY_TIMEOUT" | "LOOP" | "PLAN_MISMATCH" | "STAGNATION" | "UNKNOWN",
  "explanation": "A concise 1-2 sentence diagnosis of the execution state.",
  "confidence": float between 0.0 and 1.0,
  "confidence_level": "LOW" | "MEDIUM" | "HIGH"
}
Do NOT include markdown fences, code blocks, or text outside the JSON object.
"""


def format_judge_user_prompt(
    task_prompt: str,
    turns_prefix: List[Dict[str, Any]],
    signals: SignalVector,
    ml_risk_prob: float,
    max_recent_turns: int = 6,
) -> str:
    """
    Format user prompt with task context, recent turns, signals, and ML prediction.
    """
    # Slice the most recent turns to fit within context window while showing immediate context
    recent_turns = turns_prefix[-max_recent_turns:] if len(turns_prefix) > max_recent_turns else turns_prefix
    start_turn_idx = max(0, len(turns_prefix) - len(recent_turns))

    formatted_turns = []
    for idx, turn in enumerate(recent_turns):
        t_idx = start_turn_idx + idx
        role = turn.get("role", "unknown")
        thought = str(turn.get("thought", "") or "").strip()
        action = str(turn.get("action", "") or "").strip()
        content = str(turn.get("content", "") or "").strip()

        turn_repr = f"[Turn {t_idx} | Role: {role}]"
        if thought:
            turn_repr += f"\n  Thought: {thought[:250]}"
        if action:
            turn_repr += f"\n  Action: {action[:250]}"
        if content:
            turn_repr += f"\n  Content: {content[:250]}"
        formatted_turns.append(turn_repr)

    turns_block = "\n\n".join(formatted_turns)

    signals_summary = {
        "current_step": signals.step_idx,
        "active_retries": signals.active_retry_count,
        "consecutive_tool_failures": signals.consecutive_tool_failures,
        "tool_failure_rate": signals.tool_failure_rate,
        "loop_indicator_score": signals.loop_indicator_score,
        "action_repetition_count": signals.action_repetition_count,
        "stagnation_score": signals.stagnation_score,
        "lexical_diversity": signals.lexical_diversity,
        "plan_mismatch_score": signals.plan_mismatch_score,
        "action_diversity": signals.action_diversity,
        "isolated_failure_flag": bool(signals.isolated_failure_flag),
    }

    user_prompt = f"""### AGENT EXECUTION AUDIT REQUEST

User Task:
"{task_prompt}"

Recent Execution History (Step {start_turn_idx} to Step {signals.step_idx}):
{turns_block}

Signals Engine Runtime Metrics:
{json.dumps(signals_summary, indent=2)}

Lightweight ML Classifier Prediction:
- Estimated Failure-Risk Probability: {ml_risk_prob:.4f} (Threshold: p >= 0.50 indicates elevated risk)

Analyze whether the agent should CONTINUE or if an ALARM should be raised.
Return your evaluation as a valid JSON object matching the required schema.
"""
    return user_prompt

