from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import os
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenRouter-compatible LLM client (OpenAI-compatible API interface).

    This replaces provider-specific integrations (Gemini/Anthropic) and
    exposes the same `generate` (async) and `generate_sync` (sync) methods
    used across the codebase.
    """

    def __init__(self) -> None:
        # prefer explicit OPENROUTER_API_KEY, fall back to legacy LLM_API_KEY
        self.api_key = os.getenv("OPENROUTER_API_KEY") or getattr(settings, "llm_api_key", None)
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.chat_path = f"{self.base_url.rstrip('/')}/chat/completions"
        self.default_model = getattr(settings, "llm_model", "openai/gpt-5")
        self.fallback_model = "openai/gpt-4.1"
        self._timeout = float(os.getenv("OPENROUTER_TIMEOUT", "60"))
        self._retries = int(os.getenv("OPENROUTER_RETRIES", "3"))

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set; LLM calls will fail until configured")

    async def generate(
        self,
        prompt: str | None = None,
        *,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Async generate using OpenRouter chat completions.

        Maintains compatibility with prior `generate(prompt)` callers by
        converting single-string prompts into a single user message.
        """
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost:3000"),
            "X-OpenRouter-Title": os.getenv("OPENROUTER_TITLE", "AI Application"),
        }

        last_exc: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(1, self._retries + 1):
                try:
                    resp = await client.post(self.chat_path, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    # expected shape: {"choices": [{"message": {"content": "..."}}]}
                    choices = data.get("choices") or []
                    if choices and isinstance(choices, list):
                        msg = choices[0].get("message", {})
                        return msg.get("content", "")
                    # fallback to common fields
                    if isinstance(data, dict):
                        for key in ("output", "text", "response", "result", "content"):
                            if key in data:
                                return data[key]
                    return str(data)
                except Exception as exc:  # pylint: disable=broad-except
                    last_exc = exc
                    logger.warning("OpenRouter request failed (attempt %d/%d): %s", attempt, self._retries, exc)
                    if attempt < self._retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise

        raise last_exc or RuntimeError("OpenRouter request failed")

    def generate_sync(
        self,
        prompt: str | None = None,
        *,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Synchronous wrapper for generate.

        Converts arguments into the OpenRouter chat completion payload and performs
        a blocking HTTP request using `httpx`.
        """
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost:3000"),
            "X-OpenRouter-Title": os.getenv("OPENROUTER_TITLE", "AI Application"),
        }

        last_exc: Optional[Exception] = None
        with httpx.Client(timeout=self._timeout) as client:
            for attempt in range(1, self._retries + 1):
                try:
                    resp = client.post(self.chat_path, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices") or []
                    if choices and isinstance(choices, list):
                        msg = choices[0].get("message", {})
                        return msg.get("content", "")
                    if isinstance(data, dict):
                        for key in ("output", "text", "response", "result", "content"):
                            if key in data:
                                return data[key]
                    return str(data)
                except Exception as exc:  # pylint: disable=broad-except
                    last_exc = exc
                    logger.warning("OpenRouter sync request failed (attempt %d/%d): %s", attempt, self._retries, exc)
                    if attempt < self._retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise

        raise last_exc or RuntimeError("OpenRouter request failed")
