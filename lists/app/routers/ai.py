"""HA-lists — Goblin Tools AI endpoints.

Four features:

- POST /api/ai/breakdown  { item_id, spiciness? } → { task_id }    (async)
- POST /api/ai/estimate   { item_id }             → { estimate_min, estimate_max }  (sync)
- POST /api/ai/compile    { list_id, brain_dump } → { task_id }    (async)
- POST /api/ai/formalize  { text, tone }          → { text }       (sync)
- GET  /api/ai/jobs/{id}  → job status + logs + result

Sync endpoints are fast single-completion calls. Async endpoints run on a
daemon thread and are pollable via /api/ai/jobs/{id}. Single-flight is
enforced per-kind, so a second breakdown while one is running returns the
existing task_id instead of queueing.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database import get_connection
from ai import jobs, prompts, provider, storage_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ── Request / response models ───────────────────────────────────────────────


class BreakdownBody(BaseModel):
    item_id: int
    spiciness: int | None = None


class EstimateBody(BaseModel):
    item_id: int


class CompileBody(BaseModel):
    list_id: int
    brain_dump: str = Field(..., min_length=1)


class FormalizeBody(BaseModel):
    text: str = Field(..., min_length=1)
    tone: Literal["formal", "casual", "concise", "kind", "firm"] = "formal"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _load_item(item_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Item not found")
    return {k: row[k] for k in row.keys()}


def _ai_config_or_503() -> dict[str, Any]:
    try:
        return storage_client.get_ai_config()
    except RuntimeError as exc:
        raise HTTPException(503, f"AI unavailable: {exc}. Configure ai_provider and API key in add-on options.") from exc


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/breakdown")
def start_breakdown(body: BreakdownBody):
    """Kick off an AI subtask breakdown for an item.

    Stores the generated subtasks in the DB with ai_generated=1 when done.
    Returns the task_id to poll for progress and result.
    """
    item = _load_item(body.item_id)
    spiciness = body.spiciness if body.spiciness is not None else item["spiciness"]
    cfg = _ai_config_or_503()

    # Persist the effective spiciness back onto the item so the UI stays in sync.
    if spiciness != item["spiciness"]:
        conn = get_connection()
        conn.execute(
            "UPDATE items SET spiciness = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (max(1, min(5, int(spiciness))), body.item_id),
        )
        conn.commit()

    prompt = prompts.breakdown_prompt(
        title=item["title"], notes=item["notes"], spiciness=spiciness,
    )

    def worker(task_id: str) -> None:
        jobs.append_log(task_id, f"Breaking down item {body.item_id} at spiciness {spiciness}")
        result = provider.call_ai_json(
            prompt, cfg=cfg, emit=lambda m: jobs.append_log(task_id, m),
        )
        subtasks = result.get("subtasks") if isinstance(result, dict) else None
        if not isinstance(subtasks, list):
            raise ValueError(f"Unexpected AI response shape: {result!r}")

        conn = get_connection()
        # Remove any previous AI-generated subtasks so re-running replaces them.
        conn.execute(
            "DELETE FROM subtasks WHERE item_id = ? AND ai_generated = 1",
            (body.item_id,),
        )
        for order, title in enumerate(subtasks):
            title = str(title).strip()
            if not title:
                continue
            conn.execute(
                """INSERT INTO subtasks (item_id, title, sort_order, ai_generated)
                   VALUES (?, ?, ?, 1)""",
                (body.item_id, title[:500], order),
            )
        conn.commit()
        jobs.append_log(task_id, f"Created {len(subtasks)} subtasks")
        jobs.finalize(task_id, result={"item_id": body.item_id, "subtasks": subtasks})

    task_id, started = jobs.start_job("breakdown", worker, input_ref=str(body.item_id))
    return {"task_id": task_id, "status": "running", "reused": not started}


@router.post("/estimate")
def estimate(body: EstimateBody):
    """Synchronously estimate how long an item will take."""
    item = _load_item(body.item_id)
    cfg = _ai_config_or_503()

    prompt = prompts.estimate_prompt(title=item["title"], notes=item["notes"])
    try:
        result = provider.call_ai_json(prompt, cfg=cfg)
    except ValueError as exc:
        raise HTTPException(502, f"AI call failed: {exc}") from exc

    try:
        lo = int(result["estimate_min"])
        hi = int(result["estimate_max"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(502, f"Unexpected AI response: {result!r}") from exc
    if lo < 0 or hi < lo:
        raise HTTPException(502, f"Invalid estimate range: {lo}–{hi}")

    conn = get_connection()
    conn.execute(
        """UPDATE items SET estimate_min = ?, estimate_max = ?,
                updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
        (lo, hi, body.item_id),
    )
    conn.commit()
    return {"item_id": body.item_id, "estimate_min": lo, "estimate_max": hi}


@router.post("/compile")
def start_compile(body: CompileBody):
    """Convert a brain-dump into ordered items appended to `list_id`."""
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM lists WHERE id = ?", (body.list_id,)).fetchone():
        raise HTTPException(400, "list_id does not exist")
    cfg = _ai_config_or_503()

    prompt = prompts.compile_prompt(body.brain_dump)

    def worker(task_id: str) -> None:
        jobs.append_log(task_id, f"Compiling brain-dump into list {body.list_id}")
        result = provider.call_ai_json(
            prompt, cfg=cfg, emit=lambda m: jobs.append_log(task_id, m),
        )
        parsed = result.get("items") if isinstance(result, dict) else None
        if not isinstance(parsed, list):
            raise ValueError(f"Unexpected AI response shape: {result!r}")

        conn = get_connection()
        # Find the current max sort_order so new items append to the end.
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS m FROM items WHERE list_id = ?",
            (body.list_id,),
        ).fetchone()
        next_order = (row["m"] or -1) + 1

        created: list[dict] = []
        for entry in parsed:
            if isinstance(entry, str):
                title, notes = entry, ""
            elif isinstance(entry, dict):
                title = str(entry.get("title", "")).strip()
                notes = str(entry.get("notes") or "").strip()
            else:
                continue
            if not title:
                continue
            cursor = conn.execute(
                """INSERT INTO items (list_id, title, notes, sort_order)
                   VALUES (?, ?, ?, ?)""",
                (body.list_id, title[:500], notes, next_order),
            )
            created.append({"id": cursor.lastrowid, "title": title})
            next_order += 1
        conn.commit()
        jobs.append_log(task_id, f"Created {len(created)} items")
        jobs.finalize(task_id, result={"list_id": body.list_id, "items": created})

    task_id, started = jobs.start_job("compile", worker, input_ref=str(body.list_id))
    return {"task_id": task_id, "status": "running", "reused": not started}


@router.post("/formalize")
def formalize(body: FormalizeBody):
    """Synchronously rewrite text in a chosen tone."""
    cfg = _ai_config_or_503()
    prompt = prompts.formalize_prompt(body.text, body.tone)
    try:
        result = provider.call_ai_json(prompt, cfg=cfg)
    except ValueError as exc:
        raise HTTPException(502, f"AI call failed: {exc}") from exc
    text = result.get("text") if isinstance(result, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(502, f"Unexpected AI response: {result!r}")
    return {"text": text, "tone": body.tone}


@router.get("/jobs/{task_id}")
def get_job(task_id: str):
    task = jobs.get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task
