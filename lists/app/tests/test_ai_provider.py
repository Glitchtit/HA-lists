"""The Gemini key never lands in a URL, so a failed request cannot print it
into the add-on log. A refused request fails at once; only failures that can
pass on a second try are retried."""
from __future__ import annotations

import httpx
import pytest

from ai import provider


def _transport(seen, status=200):
    def handle(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        return httpx.Response(status, json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})
    return httpx.MockTransport(handle)


def _patch(monkeypatch, seen, status=200):
    real = httpx.Client
    monkeypatch.setattr(provider.httpx, "Client", lambda **kw: real(transport=_transport(seen, status), **kw))


def test_the_key_goes_in_a_header(monkeypatch):
    seen = {}
    _patch(monkeypatch, seen)
    provider._call_gemini("hi", "SECRET-KEY", "some-model")
    assert seen["headers"]["x-goog-api-key"] == "SECRET-KEY"
    assert "SECRET-KEY" not in seen["url"]


def test_a_failed_call_does_not_reveal_the_key(monkeypatch):
    seen = {}
    _patch(monkeypatch, seen, status=404)
    with pytest.raises(httpx.HTTPStatusError) as err:
        provider._call_gemini("hi", "SECRET-KEY", "retired-model")
    assert "SECRET-KEY" not in str(err.value)


# ── Retry rule: only what can succeed on a second try ───────────────────────

_OK = {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}
_CFG = {
    "provider": "gemini", "gemini_api_key": "SECRET-KEY", "gemini_model": "some-model",
    "claude_api_key": "SECRET-KEY", "claude_model": "some-claude",
    "ollama_url": "", "ollama_model": "",
}


def _serve(monkeypatch, answers):
    """Answer successive provider requests from `answers` (a Response, or an
    exception to raise). Returns the list of sleeps the retry loop asked for."""
    queue = list(answers)

    def handle(request: httpx.Request) -> httpx.Response:
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    real = httpx.Client
    monkeypatch.setattr(provider.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handle), **kw))
    sleeps: list[float] = []
    monkeypatch.setattr(provider.time, "sleep", sleeps.append)
    return queue, sleeps


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_a_refused_request_is_not_retried(monkeypatch, status):
    refusal = {"error": {"code": status, "message": "models/retired-model is not found"}}
    queue, sleeps = _serve(monkeypatch, [httpx.Response(status, json=refusal), httpx.Response(200, json=_OK)])
    with pytest.raises(ValueError) as err:
        provider.call_ai_json("hi", cfg=_CFG)
    assert len(queue) == 1 and sleeps == []            # one call, no waiting
    assert f"HTTP {status}" in str(err.value)
    assert "models/retired-model is not found" in str(err.value)   # the provider's own words
    assert "SECRET-KEY" not in str(err.value)


@pytest.mark.parametrize("first", [
    httpx.Response(408), httpx.Response(409), httpx.Response(429), httpx.Response(500), httpx.Response(503),
    httpx.ConnectError("no route"), httpx.ReadTimeout("too slow"),
    httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}),
])
def test_a_passing_failure_is_retried(monkeypatch, first):
    queue, sleeps = _serve(monkeypatch, [first, httpx.Response(200, json=_OK)])
    assert provider.call_ai_json("hi", cfg=_CFG) == {"ok": True}
    assert queue == [] and len(sleeps) == 1


def test_a_missing_key_fails_at_once(monkeypatch):
    queue, sleeps = _serve(monkeypatch, [])
    with pytest.raises(ValueError, match="Gemini API key not configured"):
        provider.call_ai_json("hi", cfg={**_CFG, "gemini_api_key": ""})
    assert sleeps == []


def test_claude_refusal_is_not_retried_and_the_sdk_does_not_retry_either(monkeypatch):
    import sys
    import types

    class NotFound(Exception):
        status_code = 404

    seen = {"calls": 0}

    class FakeAnthropic:
        def __init__(self, **kw):
            seen["client_kwargs"] = kw
            self.messages = self

        def create(self, **kw):
            seen["calls"] += 1
            raise NotFound("model: retired-claude")

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=FakeAnthropic))
    sleeps: list[float] = []
    monkeypatch.setattr(provider.time, "sleep", sleeps.append)

    with pytest.raises(ValueError) as err:
        provider.call_ai_json("hi", cfg={**_CFG, "provider": "claude"})
    assert seen["calls"] == 1 and sleeps == []
    assert seen["client_kwargs"]["max_retries"] == 0   # one retry loop, ours
    assert "HTTP 404" in str(err.value) and "model: retired-claude" in str(err.value)
    assert "SECRET-KEY" not in str(err.value)
