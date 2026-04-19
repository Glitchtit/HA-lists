"""HA-lists — Notes CRUD + wikilink-powered backlinks."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException

from database import get_connection
from models import BacklinkEntry, Note, NoteCreate, NoteUpdate
from routers._crud import apply_update, coerce_bool_cols
from routers._wikilinks import extract_wikilinks

router = APIRouter(prefix="/api/notes", tags=["notes"])


# ── Helpers ────────────────────────────────────────────────────────────────


def _row_to_note(row: sqlite3.Row) -> dict:
    return coerce_bool_cols(
        {k: row[k] for k in row.keys()},
        "pinned", "archived", "ai_generated",
    )


def _sync_links(conn: sqlite3.Connection, note_id: int, body: str) -> None:
    """Replace ``note_links`` rows for ``note_id`` with links parsed from ``body``.

    The caller owns the surrounding transaction — this helper never commits.
    """
    conn.execute("DELETE FROM note_links WHERE source_note_id = ?", (note_id,))
    seen: set[tuple[str, str]] = set()
    for target, kind in extract_wikilinks(body):
        key = (target.lower(), kind)
        if key in seen:
            continue
        seen.add(key)
        conn.execute(
            "INSERT OR IGNORE INTO note_links (source_note_id, target_title, link_type) "
            "VALUES (?, ?, ?)",
            (note_id, target, kind),
        )


def _snippet_for(body: str, target: str, max_len: int = 120) -> str:
    """Return up to ``max_len`` chars of ``body`` around the first link to ``target``."""
    body = body or ""
    if not body:
        return ""
    lowered = body.lower()
    needle_variants = [f"![[{target.lower()}", f"[[{target.lower()}"]
    idx = -1
    for needle in needle_variants:
        pos = lowered.find(needle)
        if pos != -1 and (idx == -1 or pos < idx):
            idx = pos
    if idx == -1:
        return body[:max_len].strip()
    start = max(0, idx - max_len // 2)
    end = min(len(body), start + max_len)
    start = max(0, end - max_len)
    return body[start:end].strip()


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/", response_model=list[Note])
async def list_notes(
    folder_id: int | None = None,
    archived: bool = False,
    pinned: bool | None = None,
    search: str | None = None,
):
    """List notes. ``archived=False`` hides archived rows (default)."""
    conn = get_connection()
    clauses: list[str] = []
    params: list = []
    if folder_id is not None:
        clauses.append("folder_id = ?")
        params.append(folder_id)
    if not archived:
        clauses.append("archived = 0")
    if pinned is not None:
        clauses.append("pinned = ?")
        params.append(1 if pinned else 0)
    if search:
        clauses.append("(title LIKE ? OR body LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])
    sql = "SELECT * FROM notes"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY pinned DESC, sort_order, updated_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_note(r) for r in rows]


@router.get("/resolve")
async def resolve_note(title: str):
    """Case-insensitive title lookup; returns ``{"note_id": …}`` or 404."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM notes WHERE LOWER(title) = LOWER(?) ORDER BY id ASC LIMIT 1",
        (title,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Note not found")
    return {"note_id": row["id"]}


@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Note not found")
    return _row_to_note(row)


@router.post("/", response_model=Note, status_code=201)
async def create_note(body: NoteCreate):
    conn = get_connection()
    if body.folder_id is not None:
        if not conn.execute(
            "SELECT 1 FROM folders WHERE id = ?", (body.folder_id,)
        ).fetchone():
            raise HTTPException(400, "folder_id does not exist")
    cursor = conn.execute(
        """INSERT INTO notes (folder_id, title, body, icon, color, pinned, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            body.folder_id,
            body.title,
            body.body,
            body.icon,
            body.color,
            1 if body.pinned else 0,
            body.sort_order,
        ),
    )
    note_id = cursor.lastrowid
    _sync_links(conn, note_id, body.body)
    conn.commit()
    return await get_note(note_id)


@router.patch("/{note_id}", response_model=Note)
async def update_note(note_id: int, body: NoteUpdate):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM notes WHERE id = ?", (note_id,)).fetchone():
        raise HTTPException(404, "Note not found")
    updates: dict = {}
    raw = body.model_dump(exclude_unset=True)
    for k, v in raw.items():
        if k in ("pinned", "archived"):
            updates[k] = 1 if v else 0
        elif k == "folder_id" and v is not None:
            if not conn.execute(
                "SELECT 1 FROM folders WHERE id = ?", (v,)
            ).fetchone():
                raise HTTPException(400, "folder_id does not exist")
            updates[k] = v
        else:
            updates[k] = v
    apply_update(conn, "notes", note_id, updates)
    if "body" in raw:
        _sync_links(conn, note_id, raw["body"] or "")
        conn.commit()
    return await get_note(note_id)


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()


@router.post("/{note_id}/duplicate", response_model=Note, status_code=201)
async def duplicate_note(note_id: int):
    conn = get_connection()
    src = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not src:
        raise HTTPException(404, "Note not found")
    folder_id = src["folder_id"]
    if folder_id is None:
        max_row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS m FROM notes WHERE folder_id IS NULL"
        ).fetchone()
    else:
        max_row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS m FROM notes WHERE folder_id = ?",
            (folder_id,),
        ).fetchone()
    next_order = (max_row["m"] if max_row["m"] is not None else -1) + 1
    cursor = conn.execute(
        """INSERT INTO notes
           (folder_id, title, body, icon, color, pinned, archived, sort_order, ai_generated)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (
            folder_id,
            (src["title"] or "") + " (copy)",
            src["body"],
            src["icon"],
            src["color"],
            src["pinned"],
            src["archived"],
            next_order,
        ),
    )
    new_id = cursor.lastrowid
    _sync_links(conn, new_id, src["body"] or "")
    conn.commit()
    return await get_note(new_id)


@router.get("/{note_id}/backlinks", response_model=list[BacklinkEntry])
async def get_backlinks(note_id: int):
    conn = get_connection()
    target = conn.execute(
        "SELECT title FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    if not target:
        raise HTTPException(404, "Note not found")
    target_title = target["title"]

    rows = conn.execute(
        """SELECT n.id AS note_id, n.title AS title, n.body AS body, nl.link_type AS link_type
             FROM note_links nl
             JOIN notes n ON n.id = nl.source_note_id
            WHERE LOWER(nl.target_title) = LOWER(?)
              AND n.id != ?
         ORDER BY n.id ASC""",
        (target_title, note_id),
    ).fetchall()

    return [
        BacklinkEntry(
            note_id=r["note_id"],
            title=r["title"],
            snippet=_snippet_for(r["body"] or "", target_title),
            link_type=r["link_type"],
        )
        for r in rows
    ]
