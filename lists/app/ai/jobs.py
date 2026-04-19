"""HA-lists — In-memory AI job registry.

Async AI operations (breakdown, compile) run on a daemon thread and write
their status back into a single-flight-per-kind `_tasks` dict.  Clients poll
`GET /api/ai/jobs/{task_id}` to see progress + logs + result.

Capped at _MAX_TASKS with done/error entries evicted FIFO.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Callable

logger = logging.getLogger(__name__)

_MAX_TASKS = 20
_tasks: dict[str, dict[str, Any]] = {}
_tasks_lock = threading.Lock()
_running_by_kind: dict[str, str] = {}


def _evict_if_needed() -> None:
    if len(_tasks) <= _MAX_TASKS:
        return
    done_ids = [k for k, v in _tasks.items() if v.get("status") in ("done", "error")]
    for k in done_ids[: len(_tasks) - _MAX_TASKS]:
        _tasks.pop(k, None)


def get_task(task_id: str) -> dict[str, Any] | None:
    with _tasks_lock:
        t = _tasks.get(task_id)
        return dict(t) if t else None


def append_log(task_id: str, msg: str) -> None:
    with _tasks_lock:
        t = _tasks.get(task_id)
        if t is not None:
            t["logs"].append(msg)


def reset_for_tests() -> None:
    """Test-only helper — clear state between tests."""
    with _tasks_lock:
        _tasks.clear()
        _running_by_kind.clear()


def start_job(
    kind: str,
    worker: Callable[[str], None],
    *,
    input_ref: str | None = None,
) -> tuple[str, bool]:
    """Register a new job and start it on a daemon thread.

    Returns (task_id, started). If a job of the same `kind` is already running,
    `started` is False and `task_id` is the existing one.
    """
    with _tasks_lock:
        existing = _running_by_kind.get(kind)
        if existing is not None:
            t = _tasks.get(existing)
            if t and t.get("status") == "running":
                return existing, False
            # Stale — clear
            _running_by_kind.pop(kind, None)

        task_id = str(uuid.uuid4())[:8]
        _tasks[task_id] = {
            "task_id": task_id,
            "kind": kind,
            "input_ref": input_ref,
            "status": "running",
            "logs": [],
            "result": None,
            "error": None,
            "started_at": time.time(),
            "finished_at": None,
        }
        _running_by_kind[kind] = task_id
        _evict_if_needed()

    def _run():
        try:
            worker(task_id)
        except Exception as exc:
            logger.exception("AI job %s (%s) failed", task_id, kind)
            with _tasks_lock:
                t = _tasks.get(task_id)
                if t is not None:
                    t["status"] = "error"
                    t["error"] = str(exc)
                    t["finished_at"] = time.time()
                    t["logs"].append(f"ERROR: {exc}")
        finally:
            with _tasks_lock:
                if _running_by_kind.get(kind) == task_id:
                    _running_by_kind.pop(kind, None)

    thread = threading.Thread(target=_run, daemon=True, name=f"ai-{kind}-{task_id}")
    thread.start()
    return task_id, True


def finalize(task_id: str, *, result: Any) -> None:
    """Mark a job as done with a result payload."""
    with _tasks_lock:
        t = _tasks.get(task_id)
        if t is not None:
            t["status"] = "done"
            t["result"] = result
            t["finished_at"] = time.time()
