"""Provider adapter for text-only chat completions.

Audio, STT, and TTS endpoints must continue using dedicated providers.
"""
from __future__ import annotations

import os
from typing import Any

import requests


class TextProviderError(RuntimeError):
    """Raised when text-provider configuration or a request is invalid."""


def _provider_config() -> tuple[str, str, str]:
    provider = os.getenv("DUBBING_TEXT_PROVIDER", "openai").strip().lower()
    if provider == "gemini":
        key = os.getenv("GEMINI_API_KEY", "").strip()
        base_url = os.getenv("GEMINI_OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai").strip().rstrip("/")
        model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash").strip()
    elif provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
        model = os.getenv("DUBBING_TEXT_MODEL", "gpt-4o-mini").strip()
    else:
        raise TextProviderError(f"Unsupported DUBBING_TEXT_PROVIDER: {provider}")
    if not key:
        secret_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
        raise TextProviderError(f"{secret_name} is required for {provider} text requests")
    if not base_url or not model:
        raise TextProviderError("Text provider base URL and model must be configured")
    return base_url, key, model


def chat_completion(messages: list[dict[str, str]], *, temperature: float = 0.2, timeout: int = 180, session: Any = requests) -> str:
    """Return assistant text from an OpenAI-compatible text chat endpoint."""
    base_url, key, model = _provider_config()
    response = session.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=timeout,
    )
    if not response.ok:
        # Provider error bodies may echo sensitive request details; do not log/raise them.
        raise TextProviderError(f"Text provider request failed with HTTP {response.status_code}")
    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise TextProviderError("Text provider returned an invalid chat-completions response") from exc
    if not isinstance(content, str) or not content.strip():
        raise TextProviderError("Text provider returned empty assistant content")
    return content.strip()
