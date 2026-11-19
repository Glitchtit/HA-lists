"""Unit tests for ha_lists service-layer pure helpers + poll loop."""

from __future__ import annotations

import asyncio
import pytest

from services import resolve_list_id, resolve_item_id


LISTS = [
    {"id": 1, "name": "Groceries"},
    {"id": 2, "name": "Birthday party"},
    {"id": 3, "name": "Work"},
]

ITEMS = [
    {"id": 10, "title": "Milk"},
    {"id": 11, "title": "Plan birthday party"},
    {"id": 12, "title": "Eggs"},
]


def test_resolve_list_id_exact():
    assert resolve_list_id("Groceries", LISTS) == 1


def test_resolve_list_id_case_and_whitespace_insensitive():
    assert resolve_list_id("  groceries ", LISTS) == 1


def test_resolve_list_id_not_found_lists_options():
    with pytest.raises(ValueError) as exc:
        resolve_list_id("Nope", LISTS)
    msg = str(exc.value)
    assert "Nope" in msg
    assert "Groceries" in msg  # surfaces available names for the agent


def test_resolve_list_id_ambiguous():
    dupes = [{"id": 1, "name": "Work"}, {"id": 2, "name": "work"}]
    with pytest.raises(ValueError) as exc:
        resolve_list_id("work", dupes)
    assert "matches" in str(exc.value).lower()


def test_resolve_item_id_exact():
    assert resolve_item_id("Eggs", ITEMS) == 12


def test_resolve_item_id_case_insensitive():
    assert resolve_item_id("plan BIRTHDAY party", ITEMS) == 11


def test_resolve_item_id_not_found():
    with pytest.raises(ValueError) as exc:
        resolve_item_id("Bananas", ITEMS)
    assert "Bananas" in str(exc.value)


from services import job_is_done, job_failed, extract_job_result


def test_job_is_done_true_only_when_done():
    assert job_is_done({"status": "done"}) is True
    assert job_is_done({"status": "running"}) is False
    assert job_is_done({"status": "error"}) is False
    assert job_is_done({}) is False


def test_job_failed_true_on_error():
    assert job_failed({"status": "error"}) is True
    assert job_failed({"status": "done"}) is False
    assert job_failed({"status": "running"}) is False


def test_extract_job_result_returns_result_payload():
    task = {"status": "done", "result": {"item_id": 5, "subtasks": ["a", "b"]}}
    assert extract_job_result(task) == {"item_id": 5, "subtasks": ["a", "b"]}


def test_extract_job_result_none_when_missing():
    assert extract_job_result({"status": "done"}) is None
    assert extract_job_result({"status": "done", "result": None}) is None


from services import poll_job


@pytest.mark.asyncio
async def test_poll_job_returns_when_done():
    calls = {"n": 0}
    states = [
        {"status": "running"},
        {"status": "running"},
        {"status": "done", "result": {"ok": True}},
    ]

    async def fake_get(task_id):
        i = min(calls["n"], len(states) - 1)
        calls["n"] += 1
        return states[i]

    async def no_sleep(_seconds):
        return None

    job = await poll_job(
        fake_get, "abc", timeout=45.0, interval=1.5, sleep=no_sleep
    )
    assert job["status"] == "done"
    assert calls["n"] == 3  # polled running, running, then done


@pytest.mark.asyncio
async def test_poll_job_returns_on_error():
    async def fake_get(task_id):
        return {"status": "error", "error": "boom"}

    async def no_sleep(_seconds):
        return None

    job = await poll_job(fake_get, "abc", timeout=45.0, interval=1.5, sleep=no_sleep)
    assert job["status"] == "error"


@pytest.mark.asyncio
async def test_poll_job_returns_last_seen_on_timeout():
    # Always running → loop must give up once the (fake) clock passes timeout.
    clock = {"t": 0.0}

    async def fake_get(task_id):
        return {"status": "running"}

    async def fake_sleep(seconds):
        clock["t"] += seconds  # advance the injected clock instead of waiting

    job = await poll_job(
        fake_get,
        "abc",
        timeout=5.0,
        interval=1.5,
        sleep=fake_sleep,
        monotonic=lambda: clock["t"],
    )
    assert job["status"] == "running"  # last-seen state returned, no exception


# ── Voice-assistant hardening ────────────────────────────────────────────────

import services as _svc  # noqa: E402
from types import SimpleNamespace  # noqa: E402


def _handlers(monkeypatch, coords, lists=(), posts=None):
    handlers = {}
    hass = SimpleNamespace(services=SimpleNamespace(
        has_service=lambda d, s: False,
        async_register=lambda d, name, handler, **kw: handlers.__setitem__(name, handler),
    ))

    async def refresh():
        return None

    async def fetch(coord):
        return list(lists)

    async def post(coord, path, payload):
        posts.append((path, payload))
        return {"id": 1}

    monkeypatch.setattr(_svc, "_coordinators",
                        lambda hass: [SimpleNamespace(async_request_refresh=refresh)] * coords)
    monkeypatch.setattr(_svc, "_fetch_lists", fetch)
    monkeypatch.setattr(_svc, "_post_json", post)
    _svc.async_register_services(hass)
    return handlers


def test_add_item_with_lists_not_set_up_is_an_error(monkeypatch):
    handlers = _handlers(monkeypatch, coords=0)
    with pytest.raises(_svc.HomeAssistantError, match="not set up"):
        asyncio.run(handlers["add_item"](SimpleNamespace(data={"list": "Todo", "title": "x"})))


def test_create_list_that_exists_makes_no_duplicate(monkeypatch):
    posts = []
    handlers = _handlers(monkeypatch, coords=1, lists=[{"id": 4, "name": "Groceries "}], posts=posts)
    result = asyncio.run(handlers["create_list"](SimpleNamespace(data={"name": "groceries"})))
    assert result["status"] == "already_exists"
    assert posts == []


def test_a_refusal_carries_the_add_on_reason():
    import httpx

    request = httpx.Request("POST", "http://lists/api/items/")
    response = httpx.Response(422, json={"detail": "due_at is not a date"}, request=request)
    err = httpx.HTTPStatusError("422", request=request, response=response)
    assert "due_at is not a date" in str(_svc._failure(err))
