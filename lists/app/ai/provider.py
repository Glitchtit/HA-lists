"""HA-lists — AI provider abstraction (Gemini / Claude / Ollama).

Mirrors `HA-storage/storage/app/ai_client.py` but consumes config from the
Storage bridge instead of a local `config` table.  Returns parsed JSON.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

from . import storage_client

logger = logging.getLogger(__name__)

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
_MAX_RETRIES = 4
_PROVIDER_TIMEOUT = 120.0


# ── Raw provider calls ──────────────────────────────────────────────────────


def _call_gemini(prompt: str, api_key: str, model: str) -> tuple[str, dict]:
    if not api_key:
        raise RuntimeError("Gemini API key not configured in Storage")
    url = f"{_GEMINI_BASE_URL}{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"},
    }
    with httpx.Client(timeout=_PROVIDER_TIMEOUT) as client:
        resp = client.post(url, json=payload, params={"key": api_key})
    if resp.status_code in (401, 403):
        storage_client.invalidate_cache()
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usageMetadata", {})
    stats = {
        "in": usage.get("promptTokenCount") or 0,
        "out": usage.get("candidatesTokenCount") or 0,
    }
    return data["candidates"][0]["content"]["parts"][0]["text"], stats


def _call_ollama(prompt: str, url: str, model: str) -> tuple[str, dict]:
    if not url:
        raise RuntimeError("Ollama URL not configured in Storage")
    with httpx.Client(timeout=_PROVIDER_TIMEOUT) as client:
        resp = client.post(
            f"{url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "format": "json",
                "stream": False,
            },
        )
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"], {
        "in": data.get("prompt_eval_count") or 0,
        "out": data.get("eval_count") or 0,
    }


def _call_claude(prompt: str, api_key: str, model: str) -> tuple[str, dict]:
    if not api_key:
        raise RuntimeError("Claude API key not configured in Storage")
    try:
        import anthropic as _anthropic
    except ImportError as exc:
        raise RuntimeError(
            "Claude provider selected but the 'anthropic' package is not installed"
        ) from exc
    client = _anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model or "claude-3-5-haiku-20241022",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage
    return response.content[0].text, {"in": usage.input_tokens, "out": usage.output_tokens}


# ── JSON extraction + retry wrapper ─────────────────────────────────────────


def _extract_json(text: str) -> str:
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        return fence.group(1)
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        return match.group(1)
    return text.strip()


def call_ai_json(
    prompt: str,
    *,
    cfg: dict[str, Any] | None = None,
    emit: Any = None,
) -> Any:
    """Call the configured AI provider and parse the response as JSON.

    Retries up to _MAX_RETRIES times with exponential back-off on transient
    errors or JSON parse failures.

    Raises:
        ValueError: if all attempts fail.
        RuntimeError: if provider configuration is missing/invalid.
    """
    if cfg is None:
        cfg = storage_client.get_ai_config()

    provider = cfg.get("provider", "gemini")
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            t0 = time.time()
            if provider == "ollama":
                raw, stats = _call_ollama(prompt, cfg["ollama_url"], cfg["ollama_model"])
            elif provider == "claude":
                raw, stats = _call_claude(prompt, cfg["claude_api_key"], cfg["claude_model"])
            else:
                raw, stats = _call_gemini(prompt, cfg["gemini_api_key"], cfg["gemini_model"])
            wall_ms = round((time.time() - t0) * 1000)

            sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw)
            if provider in ("claude", "ollama"):
                sanitized = _extract_json(sanitized)
            result = json.loads(sanitized)

            if emit:
                model_name = (
                    cfg.get("ollama_model") if provider == "ollama"
                    else cfg.get("claude_model") if provider == "claude"
                    else cfg.get("gemini_model")
                )
                emit(
                    f"  ↳ {model_name}: {stats.get('in', 0):,} in / "
                    f"{stats.get('out', 0):,} out · {wall_ms:,}ms"
                )

            return result
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "%s attempt %d/%d failed: %s",
                provider.capitalize(), attempt, _MAX_RETRIES, exc,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(2 ** attempt)

    raise ValueError(f"AI call failed after {_MAX_RETRIES} attempts: {last_exc}") from last_exc
