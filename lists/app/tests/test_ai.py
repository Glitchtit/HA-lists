"""HA-lists — AI subsystem tests.

Covers:
- Prompt assembly honours spiciness bucket
- Single-flight job registry: reruns before finish return the existing task_id
- /api/ai/breakdown creates subtasks with ai_generated=1 via mocked provider
- /api/ai/estimate writes min/max back to the item
- /api/ai/compile appends items with incrementing sort_order
- /api/ai/formalize returns rewritten text
- /api/ai/jobs/{id} returns 404 for unknown
- Storage outage → 503 degradation
"""

from __future__ import annotations

import time

import pytest


# ── Prompt tests ────────────────────────────────────────────────────────────


def test_breakdown_prompt_spiciness_clamped():
    from ai import prompts
    low = prompts.breakdown_prompt("Clean kitchen", None, 0)
    mid = prompts.breakdown_prompt("Clean kitchen", None, 3)
    high = prompts.breakdown_prompt("Clean kitchen", None, 99)
    assert "2–3 subtasks" in low            # clamped to 1
    assert "4–6 subtasks" in mid
    assert "8–12" in high                    # clamped to 5
    assert "get out of bed" in high.lower()


def test_breakdown_prompt_includes_notes_when_present():
    from ai import prompts
    p = prompts.breakdown_prompt("Pack for trip", "Flight at 06:00, carry-on only", 3)
    assert "Pack for trip" in p
    assert "Flight at 06:00" in p


def test_formalize_prompt_falls_back_to_formal_for_unknown_tone():
    from ai import prompts
    p = prompts.formalize_prompt("hey", "weird-unknown")
    assert "hey" in p


# ── Job registry tests ──────────────────────────────────────────────────────


def test_jobs_single_flight_per_kind():
    from ai import jobs
    jobs.reset_for_tests()

    # First worker blocks on an event so we can enqueue a second call while it
    # is still "running".
    import threading
    release = threading.Event()

    def slow_worker(task_id: str):
        release.wait(timeout=2)
        jobs.finalize(task_id, result={"ok": True})

    def fast_worker(task_id: str):
        jobs.finalize(task_id, result={"ok": True})

    first_id, started = jobs.start_job("breakdown", slow_worker)
    assert started is True

    second_id, started_again = jobs.start_job("breakdown", fast_worker)
    assert started_again is False
    assert second_id == first_id

    # Different kinds don't collide.
    other_id, started_other = jobs.start_job("compile", fast_worker)
    assert started_other is True
    assert other_id != first_id

    release.set()
    # Wait for the slow worker to finish so cleanup fires
    for _ in range(20):
        if jobs.get_task(first_id)["status"] == "done":
            break
        time.sleep(0.05)
    assert jobs.get_task(first_id)["status"] == "done"


def test_jobs_error_path_records_error():
    from ai import jobs
    jobs.reset_for_tests()

    def boom(task_id: str):
        raise RuntimeError("explode")

    task_id, _ = jobs.start_job("breakdown", boom)
    for _ in range(20):
        t = jobs.get_task(task_id)
        if t and t["status"] == "error":
            break
        time.sleep(0.05)
    t = jobs.get_task(task_id)
    assert t["status"] == "error"
    assert "explode" in t["error"]


# ── Endpoint tests (with mocked provider + storage) ─────────────────────────


@pytest.fixture
def ai_env(monkeypatch):
    """Force AI config + provider into a deterministic shape for tests."""
    from ai import jobs, storage_client, provider
    jobs.reset_for_tests()
    monkeypatch.setattr(
        storage_client,
        "get_ai_config",
        lambda *a, **k: {
            "provider": "gemini",
            "gemini_api_key": "test",
            "gemini_model": "test-model",
            "ollama_url": "",
            "ollama_model": "",
            "claude_api_key": "",
            "claude_model": "",
        },
    )
    # Default: fail loudly if a test forgets to stub call_ai_json
    monkeypatch.setattr(provider, "call_ai_json", lambda *a, **k: pytest.fail("unstubbed AI call"))
    yield monkeypatch


def _poll(client, task_id: str, *, timeout: float = 2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/ai/jobs/{task_id}").json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {task_id} did not finish within {timeout}s")


def test_breakdown_creates_ai_subtasks_and_bumps_spiciness(client, ai_env):
    from ai import provider
    lst = client.post("/api/lists/", json={"name": "Project"}).json()
    item = client.post("/api/items/", json={
        "list_id": lst["id"], "title": "Launch blog", "spiciness": 2,
    }).json()

    ai_env.setattr(
        provider, "call_ai_json",
        lambda *a, **k: {"subtasks": ["Pick domain", "Draft outline", "Publish"]},
    )

    resp = client.post("/api/ai/breakdown", json={"item_id": item["id"], "spiciness": 4})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reused"] is False

    done = _poll(client, body["task_id"])
    assert done["status"] == "done"
    assert done["result"]["item_id"] == item["id"]

    subs = client.get(f"/api/subtasks/?item_id={item['id']}").json()
    titles = [s["title"] for s in subs]
    assert titles == ["Pick domain", "Draft outline", "Publish"]
    assert all(s["ai_generated"] for s in subs)

    updated = client.get(f"/api/items/{item['id']}").json()
    assert updated["spiciness"] == 4


def test_breakdown_replaces_prior_ai_subtasks(client, ai_env):
    from ai import provider
    lst = client.post("/api/lists/", json={"name": "P"}).json()
    item = client.post("/api/items/", json={"list_id": lst["id"], "title": "T"}).json()

    # Manually insert: one AI-generated, one user-created
    client.post("/api/subtasks/", json={
        "item_id": item["id"], "title": "old AI step", "ai_generated": True,
    })
    client.post("/api/subtasks/", json={
        "item_id": item["id"], "title": "manual step", "ai_generated": False,
    })

    ai_env.setattr(provider, "call_ai_json", lambda *a, **k: {"subtasks": ["new1", "new2"]})
    resp = client.post("/api/ai/breakdown", json={"item_id": item["id"]})
    _poll(client, resp.json()["task_id"])

    titles = [s["title"] for s in client.get(f"/api/subtasks/?item_id={item['id']}").json()]
    assert "old AI step" not in titles
    assert "manual step" in titles
    assert "new1" in titles and "new2" in titles


def test_estimate_writes_range_back(client, ai_env):
    from ai import provider
    lst = client.post("/api/lists/", json={"name": "P"}).json()
    item = client.post("/api/items/", json={"list_id": lst["id"], "title": "Wash car"}).json()

    ai_env.setattr(
        provider, "call_ai_json", lambda *a, **k: {"estimate_min": 15, "estimate_max": 30},
    )
    resp = client.post("/api/ai/estimate", json={"item_id": item["id"]})
    assert resp.status_code == 200
    assert resp.json() == {"item_id": item["id"], "estimate_min": 15, "estimate_max": 30}

    updated = client.get(f"/api/items/{item['id']}").json()
    assert updated["estimate_min"] == 15
    assert updated["estimate_max"] == 30


def test_estimate_rejects_invalid_range(client, ai_env):
    from ai import provider
    lst = client.post("/api/lists/", json={"name": "P"}).json()
    item = client.post("/api/items/", json={"list_id": lst["id"], "title": "T"}).json()

    ai_env.setattr(provider, "call_ai_json", lambda *a, **k: {"estimate_min": 99, "estimate_max": 1})
    resp = client.post("/api/ai/estimate", json={"item_id": item["id"]})
    assert resp.status_code == 502


def test_compile_appends_items_in_order(client, ai_env):
    from ai import provider
    lst = client.post("/api/lists/", json={"name": "P"}).json()
    # Pre-existing item so sort_order starts non-zero
    client.post("/api/items/", json={"list_id": lst["id"], "title": "existing", "sort_order": 10})

    ai_env.setattr(provider, "call_ai_json", lambda *a, **k: {
        "items": [
            {"title": "First", "notes": "n1"},
            {"title": "Second"},
            "Third",  # also accept plain strings
            {"title": ""},  # should be skipped
        ]
    })
    resp = client.post("/api/ai/compile", json={"list_id": lst["id"], "brain_dump": "a b c"})
    _poll(client, resp.json()["task_id"])

    items = client.get(f"/api/items/?list_id={lst['id']}").json()
    items.sort(key=lambda i: i["sort_order"])
    new_titles = [i["title"] for i in items if i["title"] != "existing"]
    assert new_titles == ["First", "Second", "Third"]
    # Appended after the existing sort_order=10
    assert all(i["sort_order"] > 10 for i in items if i["title"] != "existing")


def test_compile_rejects_unknown_list(client, ai_env):
    resp = client.post("/api/ai/compile", json={"list_id": 9999, "brain_dump": "x"})
    assert resp.status_code == 400


def test_formalize_roundtrip(client, ai_env):
    from ai import provider
    ai_env.setattr(provider, "call_ai_json", lambda *a, **k: {"text": "Kindly please do it."})
    resp = client.post("/api/ai/formalize", json={"text": "do the thing", "tone": "formal"})
    assert resp.status_code == 200
    assert resp.json() == {"text": "Kindly please do it.", "tone": "formal"}


def test_jobs_404_for_unknown(client, ai_env):
    assert client.get("/api/ai/jobs/does-not-exist").status_code == 404


def test_storage_down_returns_503(client, monkeypatch):
    from ai import storage_client

    def boom(*a, **k):
        raise RuntimeError("Storage offline")

    monkeypatch.setattr(storage_client, "get_ai_config", boom)

    lst = client.post("/api/lists/", json={"name": "P"}).json()
    item = client.post("/api/items/", json={"list_id": lst["id"], "title": "T"}).json()

    for path, body in [
        ("/api/ai/breakdown", {"item_id": item["id"]}),
        ("/api/ai/estimate", {"item_id": item["id"]}),
        ("/api/ai/compile", {"list_id": lst["id"], "brain_dump": "x"}),
        ("/api/ai/formalize", {"text": "hi", "tone": "formal"}),
    ]:
        resp = client.post(path, json=body)
        assert resp.status_code == 503, f"{path} expected 503, got {resp.status_code}"
