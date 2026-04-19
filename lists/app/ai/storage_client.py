"""HA-lists — Bridge to HA-storage for centralised AI config.

Storage exposes `GET /api/config/ai` with the shape:

    {
      "provider": "gemini" | "claude" | "ollama",
      "api_key": "...",           # gemini key
      "model": "gemini-2.0-flash",
      "ollama_url": "...",
      "ollama_model": "...",
      "claude_api_key": "...",
      "claude_model": "..."
    }

We cache the result for a short TTL and refresh lazily.  If Storage is
unreachable, AI features raise; non-AI CRUD keeps working.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 600  # 10 minutes
_REQUEST_TIMEOUT = 10.0

_lock = threading.Lock()
_cached: dict[str, Any] | None = None
_cached_at: float = 0.0


def _default_storage_url() -> str:
    return (
        os.environ.get("STORAGE_URL")
        or "http://a0a9ed235-ha-storage:8099"
    ).rstrip("/")


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise Storage's /api/config/ai shape into the one the provider expects."""
    provider = (raw.get("provider") or "gemini").strip() or "gemini"
    return {
        "provider": provider,
        "gemini_api_key": raw.get("api_key") or raw.get("gemini_api_key") or "",
        "gemini_model": raw.get("model") or raw.get("gemini_model") or "gemini-2.0-flash",
        "ollama_url": raw.get("ollama_url") or "",
        "ollama_model": raw.get("ollama_model") or "llama3",
        "claude_api_key": raw.get("claude_api_key") or "",
        "claude_model": raw.get("claude_model") or "claude-3-5-haiku-20241022",
    }


def invalidate_cache() -> None:
    """Clear the cached config — used on 401/403 from a provider."""
    global _cached, _cached_at
    with _lock:
        _cached = None
        _cached_at = 0.0


def get_ai_config(*, force_refresh: bool = False) -> dict[str, Any]:
    """Return the AI provider config, cached for _CACHE_TTL_SEC.

    Raises:
        RuntimeError: if Storage is unreachable or returns non-200.
    """
    global _cached, _cached_at
    now = time.time()
    with _lock:
        if (
            not force_refresh
            and _cached is not None
            and now - _cached_at < _CACHE_TTL_SEC
        ):
            return dict(_cached)

    url = f"{_default_storage_url()}/api/config/ai"
    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Cannot reach Storage AI config at {url}: {exc}") from exc

    if resp.status_code != 200:
        raise RuntimeError(
            f"Storage AI config returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    cfg = _normalise(resp.json())
    with _lock:
        _cached = cfg
        _cached_at = now
    logger.info(
        "Fetched AI config from Storage (provider=%s, model=%s)",
        cfg["provider"],
        cfg.get(f"{cfg['provider']}_model") or cfg.get("gemini_model"),
    )
    return dict(cfg)


def wait_for_storage(max_retries: int = 30, delay: float = 5.0) -> bool:
    """Block until Storage is reachable. Returns True on success, False on timeout.

    Non-fatal: AI routers degrade to 503 if Storage is down; CRUD keeps running.
    """
    url = f"{_default_storage_url()}/api/health"
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
                resp = client.get(url)
            if resp.status_code == 200:
                logger.info("Storage reachable at %s", url)
                return True
        except httpx.HTTPError:
            pass
        if attempt < max_retries:
            time.sleep(delay)
    logger.warning("Storage not reachable after %d attempts (%s)", max_retries, url)
    return False
