"""The Gemini key never lands in a URL, so a failed request cannot print it
into the add-on log."""
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
