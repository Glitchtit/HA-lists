"""HA-lists — AI config reader from the add-on options file.

HA Supervisor writes the user's add-on configuration to ``/data/options.json``
at startup.  We read the relevant ``ai_*`` keys from there and expose the same
normalised dict that ``provider.py`` expects.

Supported keys in options.json:

    ai_provider          "gemini" | "claude" | "ollama"  (default: gemini)
    ai_gemini_api_key    Gemini API key
    ai_gemini_model      e.g. "gemini-2.0-flash"
    ai_claude_api_key    Anthropic API key
    ai_claude_model      e.g. "claude-3-5-haiku-20241022"
    ai_ollama_url        Ollama base URL
    ai_ollama_model      e.g. "llama3"

The file is read once and cached; call ``invalidate_cache()`` to force a fresh
read (done automatically on 401/403 from a provider).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 600  # 10 minutes
_lock = threading.Lock()
_cached: dict[str, Any] | None = None
_cached_mtime: float = 0.0


def _options_path() -> str:
    return os.environ.get("OPTIONS_PATH", "/data/options.json")


def _read_options() -> dict[str, Any]:
    path = _options_path()
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.debug("options.json not found at %s — using defaults", path)
        return {}
    except Exception as exc:
        logger.warning("Failed to read options.json: %s", exc)
        return {}


def _normalise(opts: dict[str, Any]) -> dict[str, Any]:
    provider = (opts.get("ai_provider") or "gemini").strip() or "gemini"
    return {
        "provider": provider,
        "gemini_api_key": opts.get("ai_gemini_api_key") or "",
        "gemini_model": opts.get("ai_gemini_model") or "gemini-2.0-flash",
        "claude_api_key": opts.get("ai_claude_api_key") or "",
        "claude_model": opts.get("ai_claude_model") or "claude-3-5-haiku-20241022",
        "ollama_url": opts.get("ai_ollama_url") or "",
        "ollama_model": opts.get("ai_ollama_model") or "llama3",
    }


def invalidate_cache() -> None:
    """Clear the cached config — called on 401/403 from a provider."""
    global _cached, _cached_mtime
    with _lock:
        _cached = None
        _cached_mtime = 0.0


def get_ai_config(*, force_refresh: bool = False) -> dict[str, Any]:
    """Return the AI provider config read from the add-on options file.

    Caches the result until ``invalidate_cache()`` is called or the options
    file modification time changes.

    Raises:
        RuntimeError: if the selected provider has no usable configuration
                      (missing API key / URL).
    """
    global _cached, _cached_mtime

    path = _options_path()
    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        current_mtime = 0.0

    with _lock:
        if not force_refresh and _cached is not None and current_mtime == _cached_mtime:
            return dict(_cached)

    opts = _read_options()
    cfg = _normalise(opts)

    with _lock:
        _cached = cfg
        _cached_mtime = current_mtime

    logger.info(
        "Loaded AI config from options.json (provider=%s, model=%s)",
        cfg["provider"],
        cfg.get(f"{cfg['provider']}_model") or cfg.get("gemini_model"),
    )
    return dict(cfg)

