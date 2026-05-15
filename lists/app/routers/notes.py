"""HA-lists — Notes CRUD + wikilink-powered backlinks."""

from __future__ import annotations

import re
import sqlite3
from datetime import date as date_cls, datetime

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


@router.post("/daily", response_model=Note)
async def get_or_create_daily_note(date: str | None = None, folder_id: int | None = None):
    """Return today's daily note (or one for a given ISO date), creating it if missing.

    Title format is ``YYYY-MM-DD``. Matching is case-insensitive on the title so
    that an already-existing note for that day is reused. Body is empty on first
    create; clients are free to seed it via a follow-up PATCH.
    """
    if date is None:
        iso = datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            iso = date_cls.fromisoformat(date).isoformat()
        except ValueError as exc:
            raise HTTPException(400, f"date must be YYYY-MM-DD: {exc}")

    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM notes WHERE LOWER(title) = LOWER(?) ORDER BY id ASC LIMIT 1",
        (iso,),
    ).fetchone()
    if row:
        return await get_note(row["id"])

    if folder_id is not None and not conn.execute(
        "SELECT 1 FROM folders WHERE id = ?", (folder_id,)
    ).fetchone():
        raise HTTPException(400, "folder_id does not exist")

    cursor = conn.execute(
        """INSERT INTO notes (folder_id, title, body, icon, color, pinned, sort_order)
           VALUES (?, ?, '', '📅', '', 0, 0)""",
        (folder_id, iso),
    )
    note_id = cursor.lastrowid
    conn.commit()
    return await get_note(note_id)


_TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9][\w/-]{0,49})")
_FENCE_RE = re.compile(r"```[\s\S]*?```")
_FRONTMATTER_RE = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?")


def _extract_tags_from_body(body: str) -> set[str]:
    """Extract Obsidian-style #tags from a note body.

    Considers both inline hashtags and the ``tags:`` frontmatter field
    (in either flow or block-list form). Skips fenced code blocks so
    ``# python`` syntax doesn't yield bogus tags.
    """
    tags: set[str] = set()
    if not body:
        return tags
    front = _FRONTMATTER_RE.match(body)
    if front:
        in_tags_block = False
        for raw_line in front.group(1).splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("tags:") or stripped.startswith("tag:"):
                rest = stripped.split(":", 1)[1].strip()
                if rest.startswith("[") and rest.endswith("]"):
                    for piece in rest[1:-1].split(","):
                        v = piece.strip().strip("'\"")
                        if v:
                            tags.add(v.lstrip("#"))
                    in_tags_block = False
                elif rest == "":
                    in_tags_block = True
                else:
                    tags.add(rest.strip("'\"").lstrip("#"))
                    in_tags_block = False
            elif in_tags_block and stripped.startswith("-"):
                v = stripped.lstrip("-").strip().strip("'\"")
                if v:
                    tags.add(v.lstrip("#"))
            else:
                in_tags_block = False
        body = body[front.end():]
    body_no_code = _FENCE_RE.sub(" ", body)
    for m in _TAG_RE.finditer(body_no_code):
        tags.add(m.group(1))
    return tags


@router.get("/tags")
async def get_note_tags():
    """Aggregate Obsidian-style tags from all non-archived note bodies.

    Returns a list of ``{"tag": ..., "count": N, "note_ids": [...]}`` sorted
    by count descending, then tag ascending.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, body FROM notes WHERE archived = 0"
    ).fetchall()
    buckets: dict[str, list[int]] = {}
    for r in rows:
        for tag in _extract_tags_from_body(r["body"] or ""):
            buckets.setdefault(tag, []).append(r["id"])
    out = [
        {"tag": t, "count": len(ids), "note_ids": ids}
        for t, ids in buckets.items()
    ]
    out.sort(key=lambda x: (-x["count"], x["tag"].lower()))
    return out


@router.get("/graph")
async def get_note_graph():
    """Return the full note-link graph for visualization.

    Nodes are non-archived notes; edges are wikilink/embed references that
    resolve (case-insensitively, by title or alias) to another note.
    Self-loops and dangling links to unknown titles are dropped, so the
    payload is renderable as-is by a force-directed graph.
    """
    conn = get_connection()
    note_rows = conn.execute(
        "SELECT id, title, icon FROM notes WHERE archived = 0 ORDER BY id ASC"
    ).fetchall()
    by_title: dict[str, int] = {}
    nodes: list[dict] = []
    for r in note_rows:
        nid = r["id"]
        title = r["title"] or ""
        nodes.append({"id": nid, "title": title, "icon": r["icon"] or "📄"})
        by_title.setdefault(title.lower(), nid)

    for arow in conn.execute("SELECT note_id, alias FROM note_aliases").fetchall():
        by_title.setdefault((arow["alias"] or "").lower(), arow["note_id"])

    edges: list[dict] = []
    seen: set[tuple[int, int, str]] = set()
    for row in conn.execute(
        "SELECT source_note_id, target_title, link_type FROM note_links"
    ).fetchall():
        src = row["source_note_id"]
        target = (row["target_title"] or "").lower()
        tgt = by_title.get(target)
        if tgt is None or tgt == src:
            continue
        key = (src, tgt, row["link_type"])
        if key in seen:
            continue
        seen.add(key)
        edges.append({"source": src, "target": tgt, "link_type": row["link_type"]})

    return {"nodes": nodes, "edges": edges}


@router.get("/resolve")
async def resolve_note(title: str):
    """Case-insensitive title-or-alias lookup; returns ``{"note_id": …}`` or 404.

    Falls back to ``note_aliases`` if no title matches, so wikilinks like
    ``[[Alt Name]]`` jump to the canonical note when registered as an alias.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM notes WHERE LOWER(title) = LOWER(?) ORDER BY id ASC LIMIT 1",
        (title,),
    ).fetchone()
    if not row:
        row = conn.execute(
            """SELECT n.id AS id
                 FROM note_aliases a
                 JOIN notes n ON n.id = a.note_id
                WHERE LOWER(a.alias) = LOWER(?)
                ORDER BY n.id ASC
                LIMIT 1""",
            (title,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Note not found")
    return {"note_id": row["id"]}


@router.get("/{note_id}/aliases", response_model=list[str])
async def list_aliases(note_id: int):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM notes WHERE id = ?", (note_id,)).fetchone():
        raise HTTPException(404, "Note not found")
    rows = conn.execute(
        "SELECT alias FROM note_aliases WHERE note_id = ? ORDER BY alias",
        (note_id,),
    ).fetchall()
    return [r["alias"] for r in rows]


@router.post("/{note_id}/aliases", response_model=list[str], status_code=201)
async def add_alias(note_id: int, body: dict):
    alias = str(body.get("alias", "")).strip()
    if not alias:
        raise HTTPException(400, "alias must be non-empty")
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM notes WHERE id = ?", (note_id,)).fetchone():
        raise HTTPException(404, "Note not found")
    existing = conn.execute(
        "SELECT id FROM notes WHERE LOWER(title) = LOWER(?) AND id != ?",
        (alias, note_id),
    ).fetchone()
    if existing:
        raise HTTPException(409, "alias conflicts with an existing note title")
    conn.execute(
        "INSERT OR IGNORE INTO note_aliases (note_id, alias) VALUES (?, ?)",
        (note_id, alias),
    )
    conn.commit()
    return await list_aliases(note_id)


@router.get("/{note_id}/unlinked_mentions", response_model=list[BacklinkEntry])
async def get_unlinked_mentions(note_id: int):
    """Notes whose body contains this note's title (or any alias) literally
    but does **not** also wikilink or embed it.

    Mirrors Obsidian's "Unlinked mentions" section under backlinks. Matching
    is case-insensitive on whole-word boundaries against the title/alias
    string; existing wikilinks are excluded so the user only sees text that
    *could* be linked.
    """
    conn = get_connection()
    target = conn.execute("SELECT title FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not target:
        raise HTTPException(404, "Note not found")

    titles = {target["title"]}
    for r in conn.execute(
        "SELECT alias FROM note_aliases WHERE note_id = ?", (note_id,)
    ).fetchall():
        titles.add(r["alias"])

    already = {
        (row["source_note_id"], (row["target_title"] or "").lower())
        for row in conn.execute(
            "SELECT source_note_id, target_title FROM note_links"
        ).fetchall()
    }

    out: list[BacklinkEntry] = []
    seen_source: set[int] = set()
    for row in conn.execute(
        "SELECT id, title, body FROM notes WHERE id != ? AND archived = 0",
        (note_id,),
    ).fetchall():
        if row["id"] in seen_source:
            continue
        body = row["body"] or ""
        lowered = body.lower()
        # Filter out matches that fall inside a wikilink/embed bracketed range.
        bracket_ranges: list[tuple[int, int]] = []
        for m in re.finditer(r"!?\[\[([^\]]+)\]\]", body):
            bracket_ranges.append((m.start(), m.end()))
        def _in_bracket(idx: int) -> bool:
            return any(s <= idx < e for s, e in bracket_ranges)
        for t in titles:
            if not t:
                continue
            pat = re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE)
            hits = [m for m in pat.finditer(body) if not _in_bracket(m.start())]
            if not hits:
                continue
            if (row["id"], t.lower()) in already:
                continue
            idx = hits[0].start()
            start = max(0, idx - 60)
            end = min(len(body), idx + 60)
            snippet = body[start:end].strip()
            out.append(BacklinkEntry(
                note_id=row["id"],
                title=row["title"],
                snippet=snippet,
                link_type="unlinked",
            ))
            seen_source.add(row["id"])
            break
    out.sort(key=lambda b: b.note_id)
    return out


@router.delete("/{note_id}/aliases/{alias}", status_code=204)
async def remove_alias(note_id: int, alias: str):
    conn = get_connection()
    conn.execute(
        "DELETE FROM note_aliases WHERE note_id = ? AND LOWER(alias) = LOWER(?)",
        (note_id, alias),
    )
    conn.commit()


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
