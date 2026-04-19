"""HA-lists — Global search (FTS5) and backlinks."""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from database import get_connection
from routers._wikilinks import extract_wikilinks

router = APIRouter(prefix="/api", tags=["search"])

_SNIPPET_MAX = 160


def _fts_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='search_index'"
    ).fetchone()
    return row is not None


_FTS_SANITIZE = re.compile(r'[^\w\s"*]', re.UNICODE)


def _to_fts_query(q: str) -> str:
    """Turn a user query into a safe FTS5 MATCH expression.

    Strategy: split into whitespace tokens, drop tokens with FTS5 syntax chars,
    then AND-combine with a trailing ``*`` for prefix matching. Returns an
    empty string if nothing usable remains.
    """
    cleaned = _FTS_SANITIZE.sub(" ", q or "").strip()
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return ""
    # Wrap each token in quotes and append * for prefix matching.
    return " ".join(f'"{t}"*' for t in tokens)


def _snippet(body: str, needle: str, max_len: int = _SNIPPET_MAX) -> str:
    body = (body or "").replace("\n", " ").strip()
    if not body:
        return ""
    if not needle:
        return body[:max_len]
    idx = body.lower().find(needle.lower())
    if idx == -1:
        return body[:max_len]
    start = max(0, idx - max_len // 3)
    end = min(len(body), start + max_len)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(body) else ""
    return f"{prefix}{body[start:end]}{suffix}"


@router.get("/search")
async def search(q: str = Query("", min_length=0), limit: int = 20) -> dict[str, Any]:
    """Unified search across boards, notes, and card bodies.

    Returns ``{results: [...]}`` ordered by FTS rank. Each result has
    ``{type, id, title, snippet, board_id?}``.
    """
    q = (q or "").strip()
    limit = max(1, min(limit, 50))
    if not q:
        return {"results": []}

    conn = get_connection()
    results: list[dict[str, Any]] = []

    if _fts_available(conn):
        fts_q = _to_fts_query(q)
        if fts_q:
            try:
                rows = conn.execute(
                    """
                    SELECT entity_type, entity_id, board_id, title, body,
                           snippet(search_index, 4, '', '', '…', 10) AS snip
                      FROM search_index
                     WHERE search_index MATCH ?
                     ORDER BY rank
                     LIMIT ?
                    """,
                    (fts_q, limit),
                ).fetchall()
                for r in rows:
                    snip = r["snip"] or _snippet(r["body"] or "", q)
                    results.append(
                        {
                            "type": r["entity_type"],
                            "id": r["entity_id"],
                            "title": r["title"] or ("Untitled " + r["entity_type"]),
                            "snippet": snip,
                            "board_id": r["board_id"],
                        }
                    )
            except sqlite3.OperationalError:
                results = []

    if not results:
        # LIKE fallback — used when FTS is missing or query has only stopwords.
        like = f"%{q}%"
        rows = conn.execute(
            """
            SELECT 'board' AS type, id, name AS title, '' AS body, id AS board_id
              FROM boards WHERE name LIKE ? AND COALESCE(archived,0)=0
            UNION ALL
            SELECT 'note', id, title, COALESCE(body,''), NULL
              FROM notes WHERE (title LIKE ? OR body LIKE ?) AND COALESCE(archived,0)=0
            UNION ALL
            SELECT 'card', id, COALESCE(title,''), COALESCE(body,''), board_id
              FROM board_nodes
             WHERE kind='card' AND (COALESCE(title,'') LIKE ? OR COALESCE(body,'') LIKE ?)
            LIMIT ?
            """,
            (like, like, like, like, like, limit),
        ).fetchall()
        for r in rows:
            results.append(
                {
                    "type": r["type"],
                    "id": r["id"],
                    "title": r["title"] or f"Untitled {r['type']}",
                    "snippet": _snippet(r["body"] or "", q),
                    "board_id": r["board_id"],
                }
            )

    return {"results": results}


# ── Board backlinks ───────────────────────────────────────────────────────


@router.get("/boards/{board_id}/backlinks")
async def board_backlinks(board_id: int) -> dict[str, Any]:
    """Return inbound references to this board.

    Two sources:
    - Portal nodes (``kind='board'``, ``ref_id=board_id``) on other boards.
    - Cards whose body contains a wikilink ``[[BoardName]]``.
    """
    conn = get_connection()
    board = conn.execute(
        "SELECT id, name FROM boards WHERE id = ?", (board_id,)
    ).fetchone()
    if not board:
        raise HTTPException(404, "Board not found")
    name = board["name"]

    portals = conn.execute(
        """
        SELECT n.id AS node_id, n.board_id AS board_id, b.name AS board_name, b.icon AS board_icon
          FROM board_nodes n
          JOIN boards b ON b.id = n.board_id
         WHERE n.kind = 'board' AND n.ref_id = ? AND n.board_id != ?
         ORDER BY n.board_id, n.id
        """,
        (board_id, board_id),
    ).fetchall()

    wiki_rows = conn.execute(
        """
        SELECT n.id AS node_id, n.board_id AS board_id, n.title AS title, n.body AS body,
               b.name AS board_name, b.icon AS board_icon
          FROM board_nodes n
          JOIN boards b ON b.id = n.board_id
         WHERE n.kind = 'card' AND n.board_id != ?
           AND LOWER(COALESCE(n.body,'')) LIKE ?
        """,
        (board_id, f"%[[{name.lower()}%"),
    ).fetchall()

    wiki_results = []
    for r in wiki_rows:
        for target, _ in extract_wikilinks(r["body"] or ""):
            if target.lower() == name.lower():
                wiki_results.append(
                    {
                        "type": "card",
                        "node_id": r["node_id"],
                        "board_id": r["board_id"],
                        "board_name": r["board_name"],
                        "board_icon": r["board_icon"],
                        "title": r["title"] or "Untitled card",
                        "snippet": _snippet(r["body"] or "", f"[[{name}"),
                    }
                )
                break

    return {
        "portals": [
            {
                "type": "portal",
                "node_id": p["node_id"],
                "board_id": p["board_id"],
                "board_name": p["board_name"],
                "board_icon": p["board_icon"] or "🗂️",
            }
            for p in portals
        ],
        "cards": wiki_results,
    }


# ── Extended note backlinks ───────────────────────────────────────────────


@router.get("/notes/{note_id}/board_backlinks")
async def note_board_backlinks(note_id: int) -> dict[str, Any]:
    """Inbound references to this note from boards (ref nodes + wikilinks in cards)."""
    conn = get_connection()
    note = conn.execute("SELECT id, title FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        raise HTTPException(404, "Note not found")
    title = note["title"]

    ref_rows = conn.execute(
        """
        SELECT n.id AS node_id, n.board_id AS board_id, b.name AS board_name, b.icon AS board_icon
          FROM board_nodes n
          JOIN boards b ON b.id = n.board_id
         WHERE n.kind = 'note' AND n.ref_id = ?
         ORDER BY n.board_id, n.id
        """,
        (note_id,),
    ).fetchall()

    wiki_rows = conn.execute(
        """
        SELECT n.id AS node_id, n.board_id AS board_id, n.title AS title, n.body AS body,
               b.name AS board_name, b.icon AS board_icon
          FROM board_nodes n
          JOIN boards b ON b.id = n.board_id
         WHERE n.kind = 'card' AND LOWER(COALESCE(n.body,'')) LIKE ?
        """,
        (f"%[[{title.lower()}%",),
    ).fetchall()

    cards = []
    for r in wiki_rows:
        for target, _ in extract_wikilinks(r["body"] or ""):
            if target.lower() == title.lower():
                cards.append(
                    {
                        "node_id": r["node_id"],
                        "board_id": r["board_id"],
                        "board_name": r["board_name"],
                        "board_icon": r["board_icon"],
                        "title": r["title"] or "Untitled card",
                        "snippet": _snippet(r["body"] or "", f"[[{title}"),
                    }
                )
                break

    return {
        "refs": [
            {
                "node_id": r["node_id"],
                "board_id": r["board_id"],
                "board_name": r["board_name"],
                "board_icon": r["board_icon"] or "🧩",
            }
            for r in ref_rows
        ],
        "cards": cards,
    }
