"""HA-lists — AI endpoints for notes.

All handlers are synchronous single-shot calls (no background jobs). Each one
loads a note, builds a prompt, and returns the parsed provider response with
minimal reshaping.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection
from ai import prompts, provider, storage_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/notes", tags=["ai-notes"])


# ── Request models ──────────────────────────────────────────────────────────


class NoteSummarizeBody(BaseModel):
    note_id: int


class NoteContinueBody(BaseModel):
    note_id: int
    prompt: str = ""


class NoteRewriteBody(BaseModel):
    note_id: int
    tone: Literal["formal", "casual", "concise", "kind", "firm"] = "formal"


class NoteExtractTasksBody(BaseModel):
    note_id: int
    target_list_id: int


class NoteOutlineBody(BaseModel):
    note_id: int


# ── Helpers ─────────────────────────────────────────────────────────────────


def _ai_config_or_503() -> dict[str, Any]:
    try:
        return storage_client.get_ai_config()
    except RuntimeError as exc:
        raise HTTPException(
            503,
            f"AI unavailable: {exc}. Configure ai_provider and API key in add-on options.",
        ) from exc


def _load_note(note_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Note not found")
    return {k: row[k] for k in row.keys()}


def _call_json(prompt: str, cfg: dict) -> dict:
    try:
        result = provider.call_ai_json(prompt, cfg=cfg)
    except ValueError as exc:
        raise HTTPException(502, f"AI call failed: {exc}") from exc
    if not isinstance(result, dict):
        raise HTTPException(502, f"Unexpected AI response: {result!r}")
    return result


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/summarize")
def summarize(body: NoteSummarizeBody):
    note = _load_note(body.note_id)
    cfg = _ai_config_or_503()
    result = _call_json(prompts.note_summarize_prompt(note["body"] or ""), cfg)
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise HTTPException(502, f"Unexpected AI response: {result!r}")
    return {"note_id": body.note_id, "summary": summary}


@router.post("/continue")
def continue_note(body: NoteContinueBody):
    note = _load_note(body.note_id)
    cfg = _ai_config_or_503()
    result = _call_json(
        prompts.note_continue_prompt(note["body"] or "", body.prompt or ""),
        cfg,
    )
    continuation = result.get("continuation")
    if not isinstance(continuation, str) or not continuation.strip():
        raise HTTPException(502, f"Unexpected AI response: {result!r}")
    return {"note_id": body.note_id, "continuation": continuation}


@router.post("/rewrite")
def rewrite(body: NoteRewriteBody):
    note = _load_note(body.note_id)
    cfg = _ai_config_or_503()
    result = _call_json(
        prompts.note_rewrite_prompt(note["body"] or "", body.tone),
        cfg,
    )
    new_body = result.get("body")
    if not isinstance(new_body, str) or not new_body.strip():
        raise HTTPException(502, f"Unexpected AI response: {result!r}")
    return {"note_id": body.note_id, "body": new_body, "tone": body.tone}


@router.post("/outline")
def outline(body: NoteOutlineBody):
    note = _load_note(body.note_id)
    cfg = _ai_config_or_503()
    result = _call_json(prompts.note_outline_prompt(note["body"] or ""), cfg)
    outline_text = result.get("outline")
    if not isinstance(outline_text, str) or not outline_text.strip():
        raise HTTPException(502, f"Unexpected AI response: {result!r}")
    return {"note_id": body.note_id, "outline": outline_text}


@router.post("/extract-tasks")
def extract_tasks(body: NoteExtractTasksBody):
    note = _load_note(body.note_id)
    conn = get_connection()
    if not conn.execute(
        "SELECT 1 FROM lists WHERE id = ?", (body.target_list_id,)
    ).fetchone():
        raise HTTPException(400, "target_list_id does not exist")

    cfg = _ai_config_or_503()
    result = _call_json(prompts.note_extract_tasks_prompt(note["body"] or ""), cfg)
    tasks = result.get("tasks")
    if not isinstance(tasks, list):
        raise HTTPException(502, f"Unexpected AI response: {result!r}")

    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) AS m FROM items WHERE list_id = ?",
        (body.target_list_id,),
    ).fetchone()
    next_order = (row["m"] if row["m"] is not None else -1) + 1

    created: list[dict] = []
    for entry in tasks:
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
            (body.target_list_id, title[:500], notes, next_order),
        )
        created.append({"id": cursor.lastrowid, "title": title})
        next_order += 1
    conn.commit()
    return {"note_id": body.note_id, "list_id": body.target_list_id, "created": created}
