from __future__ import annotations

import json
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    import anthropic
except Exception:
    anthropic = None


class LLMClient:
    """Unified LLM client supporting Gemini, Anthropic (Claude), and HTTP endpoints."""

    def __init__(self):
        self.provider = (getattr(settings, "llm_provider", "") or "gemini").lower()
        self.api_key = getattr(settings, "llm_api_key", None)
        self.api_url = getattr(settings, "llm_api_url", None)
        self.model = getattr(settings, "llm_model", None)

        self.client = None

        if self.provider == "gemini" and genai is not None and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model or "gemini-pro")
            except Exception:
                logger.exception("Failed to initialize Gemini client")

        if self.provider in ("anthropic", "claude") and anthropic is not None and self.api_key:
            try:
                # anthropic.Client may be sync-only; keep client for sync calls
                self.client = anthropic.Client(api_key=self.api_key)
            except Exception:
                logger.exception("Failed to initialize Anthropic client")

    async def generate(self, prompt: str, temperature: float = 0.1, max_tokens: int = 512) -> str:
        """Generate text from configured LLM.

        Returns the textual output. Raises exceptions on failure.
        """
        # Gemini path (sync SDK) - call synchronously
        if self.provider == "gemini" and self.client is not None:
            resp = self.client.generate_content(
                prompt,
                generation_config={"temperature": temperature, "max_tokens": max_tokens},
            )
            return getattr(resp, "text", str(resp))

        # Anthropic/Claude path (sync client) - run in thread
        if self.provider in ("anthropic", "claude") and self.client is not None:
            import asyncio

            def _call_anthropic():
                try:
                    # Use the common completions API shape
                    return self.client.completions.create(
                        model=self.model or "claude-2.1",
                        prompt=prompt,
                        max_tokens_to_sample=max_tokens,
                    )
                except Exception as exc:
                    logger.exception("Anthropic request failed: %s", exc)
                    raise

            resp = await asyncio.to_thread(_call_anthropic)
            if hasattr(resp, "completion"):
                return resp.completion
            if isinstance(resp, dict):
                return resp.get("completion") or resp.get("text") or json.dumps(resp)
            return str(resp)

        # HTTP fallback (self-hosted Claude or other compatible endpoints)
        if self.api_url:
            import httpx

            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            payload = {"prompt": prompt}
            if self.model:
                payload["model"] = self.model

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.api_url, json=payload, headers=headers)
                resp.raise_for_status()
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        for key in ("output", "text", "response", "result", "content"):
                            if key in data:
                                return data[key]
                        return json.dumps(data)
                    return str(data)
                except Exception:
                    return resp.text

        raise RuntimeError("No LLM provider configured or client not initialized")

    def generate_sync(self, prompt: str, temperature: float = 0.1, max_tokens: int = 512) -> str:
        """Synchronous wrapper for `generate` for callers in sync contexts."""
        # Gemini (sync): use client directly
        if self.provider == "gemini" and self.client is not None:
            resp = self.client.generate_content(
                prompt,
                generation_config={"temperature": temperature, "max_tokens": max_tokens},
            )
            return getattr(resp, "text", str(resp))

        # Anthropic (sync client)
        if self.provider in ("anthropic", "claude") and self.client is not None:
            resp = self.client.completions.create(
                model=self.model or "claude-2.1",
                prompt=prompt,
                max_tokens_to_sample=max_tokens,
            )
            if hasattr(resp, "completion"):
                return resp.completion
            if isinstance(resp, dict):
                return resp.get("completion") or resp.get("text") or json.dumps(resp)
            return str(resp)

        # HTTP sync fallback
        if self.api_url:
            import httpx

            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            payload = {"prompt": prompt}
            if self.model:
                payload["model"] = self.model

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(self.api_url, json=payload, headers=headers)
                resp.raise_for_status()
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        for key in ("output", "text", "response", "result", "content"):
                            if key in data:
                                return data[key]
                        return json.dumps(data)
                    return str(data)
                except Exception:
                    return resp.text

        raise RuntimeError("No LLM provider configured or client not initialized")
