"""Lists – HA service handlers + agent-facing services.

Five services let an LLM/voice agent drive the Lists add-on:

  - ha_lists.create_list       (write)              POST /api/lists/
  - ha_lists.add_item          (write)              POST /api/items/
  - ha_lists.breakdown_item    (response: ONLY)     POST /api/ai/breakdown → poll → subtasks
  - ha_lists.compile_braindump (response: ONLY)     POST /api/ai/compile   → poll → items
  - ha_lists.find_lists        (response: ONLY)     GET  /api/lists/

Pure helpers (resolve_*/job parsing/poll loop) are unit-tested; handlers are
thin HTTP glue over the existing ListsCoordinator.addon_url, mirroring the
ha_storage services pattern.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

import httpx
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import ListsCoordinator

_LOGGER = logging.getLogger(__name__)

# Bounded poll budget for async AI jobs.
JOB_TIMEOUT_S = 45.0
JOB_POLL_INTERVAL_S = 1.5


# ── Pure helpers (unit-tested, no HTTP / no HA) ──────────────────────────────


def resolve_list_id(name: str, lists: list[dict]) -> int:
    """Resolve a list name to its id (case-insensitive, trimmed).

    Raises ValueError (agent-friendly) on no match or ambiguous match.
    """
    needle = (name or "").strip().lower()
    matches = [l for l in lists if str(l.get("name", "")).strip().lower() == needle]
    if not matches:
        available = ", ".join(sorted(str(l.get("name", "")) for l in lists)) or "(none)"
        raise ValueError(f"No list named '{name}'. Available lists: {available}")
    if len(matches) > 1:
        raise ValueError(
            f"List name '{name}' matches {len(matches)} lists; rename one or use its id."
        )
    return int(matches[0]["id"])


def resolve_item_id(title: str, items: list[dict]) -> int:
    """Resolve an item title to its id (case-insensitive, trimmed)."""
    needle = (title or "").strip().lower()
    matches = [i for i in items if str(i.get("title", "")).strip().lower() == needle]
    if not matches:
        available = ", ".join(str(i.get("title", "")) for i in items) or "(none)"
        raise ValueError(f"No item titled '{title}'. Items in list: {available}")
    if len(matches) > 1:
        raise ValueError(
            f"Item title '{title}' matches {len(matches)} items; be more specific."
        )
    return int(matches[0]["id"])


def job_is_done(job: dict) -> bool:
    """True when the AI job finished successfully."""
    return job.get("status") == "done"


def job_failed(job: dict) -> bool:
    """True when the AI job ended in error."""
    return job.get("status") == "error"


def extract_job_result(job: dict) -> Any | None:
    """Return the job's result payload (or None if absent)."""
    return job.get("result")


async def poll_job(
    get_fn: Callable[[str], Awaitable[dict]],
    task_id: str,
    *,
    timeout: float = JOB_TIMEOUT_S,
    interval: float = JOB_POLL_INTERVAL_S,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    monotonic: Callable[[], float] = None,
) -> dict:
    """Poll `get_fn(task_id)` until the job is done/error or `timeout` elapses.

    Returns the last task dict seen. `sleep` and `monotonic` are injectable so
    the logic is testable without real waiting. On timeout, returns the last
    (still-running) task dict — the caller decides how to report that.
    """
    clock = monotonic or asyncio.get_event_loop().time
    deadline = clock() + timeout
    job: dict = {"status": "running", "task_id": task_id}
    while True:
        job = await get_fn(task_id)
        if job_is_done(job) or job_failed(job):
            return job
        if clock() >= deadline:
            return job
        await sleep(interval)


# ── Service names ────────────────────────────────────────────────────────────

SERVICE_CREATE_LIST = "create_list"
SERVICE_ADD_ITEM = "add_item"
SERVICE_BREAKDOWN_ITEM = "breakdown_item"
SERVICE_COMPILE_BRAINDUMP = "compile_braindump"
SERVICE_FIND_LISTS = "find_lists"


# ── Schemas ──────────────────────────────────────────────────────────────────

_CREATE_LIST_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("icon"): cv.string,
        vol.Optional("color"): cv.string,
        vol.Optional("folder_id"): vol.Any(None, vol.Coerce(int)),
    }
)

_ADD_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required("list"): cv.string,
        vol.Required("title"): cv.string,
        vol.Optional("notes"): cv.string,
        vol.Optional("assigned_to"): cv.string,
        vol.Optional("due_at"): cv.string,
        vol.Optional("priority"): vol.Coerce(int),
        vol.Optional("spiciness"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
    }
)

_BREAKDOWN_SCHEMA = vol.Schema(
    {
        vol.Required("list"): cv.string,
        vol.Required("item"): cv.string,
        vol.Optional("spiciness"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
    }
)

_COMPILE_SCHEMA = vol.Schema(
    {
        vol.Required("list"): cv.string,
        vol.Required("brain_dump"): cv.string,
    }
)

_FIND_LISTS_SCHEMA = vol.Schema({})


# ── HTTP glue ──────────────────────────────────────────────────────────────


def _coordinators(hass: HomeAssistant) -> list[ListsCoordinator]:
    return [v for v in hass.data.get(DOMAIN, {}).values() if isinstance(v, ListsCoordinator)]


async def _get_json(coord: ListsCoordinator, path: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{coord.addon_url}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()


async def _post_json(coord: ListsCoordinator, path: str, payload: dict) -> Any:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{coord.addon_url}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()


async def _fetch_lists(coord: ListsCoordinator) -> list[dict]:
    return await _get_json(coord, "/api/lists/")


# ── Registration ──────────────────────────────────────────────────────────


def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services. Idempotent."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_LIST):
        return

    async def handle_create_list(call: ServiceCall) -> None:
        payload = {k: v for k, v in call.data.items() if v is not None}
        for coord in _coordinators(hass):
            await _post_json(coord, "/api/lists/", payload)
            await coord.async_request_refresh()

    async def handle_add_item(call: ServiceCall) -> None:
        list_name = call.data["list"]
        payload = {
            k: v
            for k, v in call.data.items()
            if k != "list" and v is not None
        }
        for coord in _coordinators(hass):
            lists = await _fetch_lists(coord)
            payload["list_id"] = resolve_list_id(list_name, lists)
            await _post_json(coord, "/api/items/", payload)
            await coord.async_request_refresh()

    async def handle_breakdown(call: ServiceCall) -> dict:
        coords = _coordinators(hass)
        if not coords:
            return {"status": "error", "error": "no_coordinator"}
        coord = coords[0]
        lists = await _fetch_lists(coord)
        list_id = resolve_list_id(call.data["list"], lists)
        items = await _get_json(coord, "/api/items/", {"list_id": list_id})
        item_id = resolve_item_id(call.data["item"], items)

        body: dict = {"item_id": item_id}
        if "spiciness" in call.data:
            body["spiciness"] = call.data["spiciness"]
        start = await _post_json(coord, "/api/ai/breakdown", body)
        task_id = start["task_id"]

        async def _get(tid: str) -> dict:
            return await _get_json(coord, f"/api/ai/jobs/{tid}")

        job = await poll_job(_get, task_id)
        if job_failed(job):
            return {"status": "error", "task_id": task_id, "error": job.get("error")}
        if not job_is_done(job):
            return {"status": "timeout", "task_id": task_id}

        subtasks = await _get_json(coord, "/api/subtasks/", {"item_id": item_id})
        await coord.async_request_refresh()
        return {
            "status": "done",
            "task_id": task_id,
            "item_id": item_id,
            "subtasks": [s["title"] for s in subtasks],
        }

    async def handle_compile(call: ServiceCall) -> dict:
        coords = _coordinators(hass)
        if not coords:
            return {"status": "error", "error": "no_coordinator"}
        coord = coords[0]
        lists = await _fetch_lists(coord)
        list_id = resolve_list_id(call.data["list"], lists)

        start = await _post_json(
            coord,
            "/api/ai/compile",
            {"list_id": list_id, "brain_dump": call.data["brain_dump"]},
        )
        task_id = start["task_id"]

        async def _get(tid: str) -> dict:
            return await _get_json(coord, f"/api/ai/jobs/{tid}")

        job = await poll_job(_get, task_id)
        if job_failed(job):
            return {"status": "error", "task_id": task_id, "error": job.get("error")}
        if not job_is_done(job):
            return {"status": "timeout", "task_id": task_id}

        items = await _get_json(coord, "/api/items/", {"list_id": list_id})
        await coord.async_request_refresh()
        return {
            "status": "done",
            "task_id": task_id,
            "list_id": list_id,
            "items": [{"id": i["id"], "title": i["title"]} for i in items],
        }

    async def handle_find_lists(call: ServiceCall) -> dict:
        coords = _coordinators(hass)
        if not coords:
            return {"lists": []}
        lists = await _fetch_lists(coords[0])
        return {"lists": [{"id": l["id"], "name": l["name"]} for l in lists]}

    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_LIST, handle_create_list, schema=_CREATE_LIST_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_ITEM, handle_add_item, schema=_ADD_ITEM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_BREAKDOWN_ITEM,
        handle_breakdown,
        schema=_BREAKDOWN_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPILE_BRAINDUMP,
        handle_compile,
        schema=_COMPILE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FIND_LISTS,
        handle_find_lists,
        schema=_FIND_LISTS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    for svc in (
        SERVICE_CREATE_LIST,
        SERVICE_ADD_ITEM,
        SERVICE_BREAKDOWN_ITEM,
        SERVICE_COMPILE_BRAINDUMP,
        SERVICE_FIND_LISTS,
    ):
        if hass.services.has_service(DOMAIN, svc):
            hass.services.async_remove(DOMAIN, svc)
