"""
LLM Client Interface for LLM Judge.
Supports Google Gemini, OpenAI-compatible APIs, and an offline rule-assisted Mock client.
"""

from abc import ABC, abstractmethod
import json
import os
import re
from typing import Optional
import httpx


class BaseLLMClient(ABC):
    """Abstract interface for LLM calls."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 15.0) -> str:
        """Generate text from the LLM given system and user prompts."""
        pass


class GeminiClient(BaseLLMClient):
    """Google Gemini API client using standard REST endpoints."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiClient.")
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        )

    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 15.0) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(self.endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini API returned no candidates.")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise RuntimeError("Gemini API candidate content is empty.")
            return parts[0].get("text", "")


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible client (OpenAI, Groq, DeepSeek, Local Ollama/vLLM)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model
        if not self.api_key and "localhost" not in self.base_url:
            raise ValueError("OPENAI_API_KEY is required for OpenAIClient.")

    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 15.0) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


class MockLLMClient(BaseLLMClient):
    """
    Deterministic offline mock client for testing, local CI, and fallback.
    Synthesizes valid JSON responses based on signals and ML risk probability.
    """

    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 15.0) -> str:
        # Extract ML probability and signals from user prompt text
        prob_match = re.search(r"Estimated Failure-Risk Probability:\s*([\d\.]+)", user_prompt)
        p = float(prob_match.group(1)) if prob_match else 0.2

        has_loop = "loop_indicator_score" in user_prompt and (
            '"loop_indicator_score": 0.' not in user_prompt or '"action_repetition_count": 0' not in user_prompt
        )
        has_tool_fail = '"consecutive_tool_failures": 0' not in user_prompt or '"tool_failure_rate": 0.0' not in user_prompt
        has_stagnation = '"stagnation_score": 0.0' not in user_prompt

        # Determine verdict and category
        if p >= 0.55:
            verdict = "ALARM"
            if "LOOP" in user_prompt or has_loop:
                category = "LOOP"
                explanation = "Agent is trapped in repetitive action or thought cycle."
            elif has_tool_fail:
                category = "TOOL_FAILURE"
                explanation = "Unrecovered tool execution failures detected with elevated failure probability."
            elif has_stagnation:
                category = "STAGNATION"
                explanation = "Agent execution is stagnant with no progress across recent turns."
            else:
                category = "PLAN_MISMATCH"
                explanation = "Agent is deviating significantly from user task objectives."
            confidence = min(0.95, round(0.5 + (p - 0.5) * 0.9, 2))
            level = "HIGH" if confidence > 0.75 else "MEDIUM"
        else:
            verdict = "CONTINUE"
            if '"isolated_failure_flag": true' in user_prompt:
                category = "TEMPORARY_TIMEOUT"
                explanation = "Isolated tool failure observed, but agent has not entered a retry loop."
                confidence = 0.70
                level = "MEDIUM"
            else:
                category = "UNKNOWN"
                explanation = "Execution metrics are within healthy nominal bounds. No alarm indicated."
                confidence = round(0.85 - p * 0.5, 2)
                level = "HIGH" if confidence > 0.75 else "MEDIUM"

        response_dict = {
            "verdict": verdict,
            "reason_category": category,
            "explanation": explanation,
            "confidence": confidence,
            "confidence_level": level,
        }
        return json.dumps(response_dict)


def get_default_llm_client() -> BaseLLMClient:
    """Factory to instantiate client based on environment variables."""
    provider = os.getenv("LLM_PROVIDER", "").lower()

    if provider == "gemini" or (not provider and os.getenv("GEMINI_API_KEY")):
        try:
            return GeminiClient()
        except Exception:
            pass

    if provider == "openai" or (not provider and os.getenv("OPENAI_API_KEY")):
        try:
            return OpenAIClient()
        except Exception:
            pass

    # Default to MockLLMClient for reliable zero-token offline testing & development
    return MockLLMClient()

