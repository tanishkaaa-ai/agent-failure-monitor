"""
LLM Client Interface for LLM Judge.
Supports xAI Grok, Google Gemini, OpenAI-compatible APIs, and an offline rule-assisted Mock client.
"""

from abc import ABC, abstractmethod
import json
import os
import re
from typing import Optional
from dotenv import load_dotenv
import httpx

# Load .env file automatically
load_dotenv()


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


class GroqClient(BaseLLMClient):
    """Groq API client (ultra-fast inference at https://api.groq.com/openai/v1)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        raw_key = (
            api_key
            or os.getenv("GROQ_API_KEY")
            or os.getenv("GROK_API_KEY")
            or os.getenv("XAI_API_KEY", "")
        )
        # Clean prefix if 'xai-' was prepended to a Groq 'gsk_' key
        if raw_key.startswith("xai-gsk_"):
            raw_key = raw_key[4:]
        self.api_key = raw_key
        # Default to available Groq fast chat model
        self.model = (
            model
            or os.getenv("GROQ_MODEL")
            or os.getenv("GROK_MODEL")
            or "qwen/qwen3.8-27b"
        )
        if self.model == "grok-2-latest":  # User set Grok model on Groq key
            self.model = "qwen/qwen3.8-27b"
        self.base_url = (base_url or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")).rstrip("/")
        if not self.api_key or "your_" in self.api_key:
            raise ValueError("A valid GROQ_API_KEY is required for GroqClient.")

    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 15.0) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            # Automatic backoff if hitting Groq free-tier rate limits (429)
            if resp.status_code == 429:
                import time
                time.sleep(1.5)
                resp = client.post(url, headers=headers, json=payload)

            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError(f"Groq API returned no choices: {data}")
            return choices[0]["message"]["content"]


class GrokClient(BaseLLMClient):
    """xAI Grok API client (OpenAI-compatible endpoint at https://api.x.ai/v1)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY", "")
        self.model = model or os.getenv("GROK_MODEL", "grok-2-latest")
        self.base_url = (base_url or os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")).rstrip("/")
        if not self.api_key or "your_" in self.api_key:
            raise ValueError(
                "A valid GROK_API_KEY (or XAI_API_KEY) is required for GrokClient. "
                "Please set your xAI API key in .env."
            )

    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 20.0) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError(f"Grok API returned no choices: {data}")
            return choices[0]["message"]["content"]


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
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "").lower()
    key_candidate = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("GROK_API_KEY")
        or os.getenv("XAI_API_KEY", "")
    )

    # 1. Check Groq (keys starting with gsk_ or xai-gsk_)
    if provider == "groq" or key_candidate.startswith("gsk_") or key_candidate.startswith("xai-gsk_"):
        try:
            return GroqClient()
        except Exception:
            pass

    # 2. Check xAI Grok (standard xAI keys)
    if provider in ("grok", "xai") or key_candidate.startswith("xai-"):
        try:
            return GrokClient()
        except Exception:
            pass

    # 3. Check Gemini
    if provider == "gemini" or (not provider and os.getenv("GEMINI_API_KEY")):
        try:
            return GeminiClient()
        except Exception:
            pass

    # 3. Check OpenAI
    if provider == "openai" or (not provider and os.getenv("OPENAI_API_KEY")):
        try:
            return OpenAIClient()
        except Exception:
            pass

    # Default to MockLLMClient for reliable zero-token offline testing & development
    return MockLLMClient()

