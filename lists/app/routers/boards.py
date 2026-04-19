"""HA-lists — Boards (canvas/whiteboard) CRUD + nodes + edges."""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, HTTPException

from database import get_connection
from models import (
    Board,
    BoardCreate,
    BoardDetail,
    BoardEdge,
    BoardEdgeCreate,
    BoardEdgeUpdate,
    BoardNode,
    BoardNodeBulkPositions,
    BoardNodeCreate,
    BoardNodeUpdate,
    BoardUpdate,
    ViewportUpdate,
)
from routers._crud import apply_update, coerce_bool_cols
from routers._duplicate import duplicate_board

router = APIRouter(prefix="/api/boards", tags=["boards"])


DEFAULT_VIEWPORT = {"x": 0, "y": 0, "zoom": 1}


# ── Helpers ───────────────────────────────────────────────────────────────


def _parse_viewport(raw: str | None) -> dict:
    if not raw:
        return dict(DEFAULT_VIEWPORT)
    try:
        vp = json.loads(raw)
        if not isinstance(vp, dict):
            return dict(DEFAULT_VIEWPORT)
        return vp
    except Exception:
        return dict(DEFAULT_VIEWPORT)


def _row_to_board(row: sqlite3.Row) -> dict:
    data = {k: row[k] for k in row.keys()}
    data = coerce_bool_cols(data, "pinned", "archived")
    data["viewport"] = _parse_viewport(data.get("viewport"))
    return data


def _row_to_node(row: sqlite3.Row, ref_summary: dict | None = None) -> dict:
    data = {k: row[k] for k in row.keys()}
    data["ref_summary"] = ref_summary
    return data


def _row_to_edge(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def _require_board(conn: sqlite3.Connection, board_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM boards WHERE id = ?", (board_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Board not found")
    return row


def _require_node(
    conn: sqlite3.Connection, board_id: int, node_id: int
) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM board_nodes WHERE id = ? AND board_id = ?",
        (node_id, board_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Node not found")
    return row


def _build_ref_summaries(
    conn: sqlite3.Connection, nodes: list[sqlite3.Row]
) -> dict[int, dict | None]:
    """Return {node_id: ref_summary_or_None} for list/note kinded nodes."""
    list_ref_ids = [n["ref_id"] for n in nodes if n["kind"] == "list" and n["ref_id"]]
    note_ref_ids = [n["ref_id"] for n in nodes if n["kind"] == "note" and n["ref_id"]]

    list_info: dict[int, dict] = {}
    if list_ref_ids:
        placeholders = ",".join("?" * len(list_ref_ids))
        rows = conn.execute(
            f"""SELECT l.id, l.name, l.icon, l.color,
                       COUNT(i.id) AS item_count,
                       SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) AS completed_count
                  FROM lists l
                  LEFT JOIN items i ON i.list_id = l.id
                 WHERE l.id IN ({placeholders})
              GROUP BY l.id""",
            list_ref_ids,
        ).fetchall()
        for r in rows:
            list_info[r["id"]] = {
                "id": r["id"],
                "name": r["name"],
                "icon": r["icon"],
                "color": r["color"],
                "item_count": int(r["item_count"] or 0),
                "completed_count": int(r["completed_count"] or 0),
            }

    note_info: dict[int, dict] = {}
    if note_ref_ids:
        placeholders = ",".join("?" * len(note_ref_ids))
        rows = conn.execute(
            f"SELECT id, title, icon, body FROM notes WHERE id IN ({placeholders})",
            note_ref_ids,
        ).fetchall()
        for r in rows:
            body = r["body"] or ""
            note_info[r["id"]] = {
                "id": r["id"],
                "title": r["title"],
                "icon": r["icon"],
                "body_preview": body[:400],
            }

    summaries: dict[int, dict | None] = {}
    for n in nodes:
        if n["kind"] == "list":
            summaries[n["id"]] = list_info.get(n["ref_id"]) if n["ref_id"] else None
        elif n["kind"] == "note":
            summaries[n["id"]] = note_info.get(n["ref_id"]) if n["ref_id"] else None
        else:
            summaries[n["id"]] = None
    return summaries


# ── Boards ────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[Board])
async def list_boards(
    folder_id: int | None = None,
    archived: bool = False,
    pinned: bool | None = None,
    search: str | None = None,
):
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
        clauses.append("name LIKE ?")
        params.append(f"%{search}%")
    sql = "SELECT * FROM boards"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY pinned DESC, sort_order, updated_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_board(r) for r in rows]


@router.get("/{board_id}", response_model=BoardDetail)
async def get_board(board_id: int):
    conn = get_connection()
    row = _require_board(conn, board_id)
    nodes = conn.execute(
        "SELECT * FROM board_nodes WHERE board_id = ? ORDER BY z, id",
        (board_id,),
    ).fetchall()
    edges = conn.execute(
        "SELECT * FROM board_edges WHERE board_id = ? ORDER BY id",
        (board_id,),
    ).fetchall()
    summaries = _build_ref_summaries(conn, nodes)
    return {
        "board": _row_to_board(row),
        "nodes": [_row_to_node(n, summaries.get(n["id"])) for n in nodes],
        "edges": [_row_to_edge(e) for e in edges],
    }


@router.post("/", response_model=Board, status_code=201)
async def create_board(body: BoardCreate):
    conn = get_connection()
    if body.folder_id is not None:
        if not conn.execute(
            "SELECT 1 FROM folders WHERE id = ?", (body.folder_id,)
        ).fetchone():
            raise HTTPException(400, "folder_id does not exist")
    cursor = conn.execute(
        """INSERT INTO boards
           (folder_id, name, icon, color, pinned, sort_order)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            body.folder_id,
            body.name,
            body.icon,
            body.color,
            1 if body.pinned else 0,
            body.sort_order,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM boards WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_board(row)


@router.patch("/{board_id}", response_model=Board)
async def update_board(board_id: int, body: BoardUpdate):
    conn = get_connection()
    _require_board(conn, board_id)
    updates: dict = {}
    for k, v in body.model_dump(exclude_unset=True).items():
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
    apply_update(conn, "boards", board_id, updates)
    row = conn.execute("SELECT * FROM boards WHERE id = ?", (board_id,)).fetchone()
    return _row_to_board(row)


@router.delete("/{board_id}", status_code=204)
async def delete_board(board_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    conn.commit()


@router.patch("/{board_id}/viewport", response_model=Board)
async def update_viewport(board_id: int, body: ViewportUpdate):
    conn = get_connection()
    _require_board(conn, board_id)
    vp_json = json.dumps({"x": body.x, "y": body.y, "zoom": body.zoom})
    apply_update(conn, "boards", board_id, {"viewport": vp_json})
    row = conn.execute("SELECT * FROM boards WHERE id = ?", (board_id,)).fetchone()
    return _row_to_board(row)


@router.post("/{board_id}/duplicate", response_model=Board, status_code=201)
async def duplicate_board_endpoint(board_id: int):
    conn = get_connection()
    _require_board(conn, board_id)
    new_id = duplicate_board(conn, board_id)
    row = conn.execute("SELECT * FROM boards WHERE id = ?", (new_id,)).fetchone()
    return _row_to_board(row)


# ── Nodes ─────────────────────────────────────────────────────────────────


@router.post("/{board_id}/nodes", response_model=BoardNode, status_code=201)
async def create_node(board_id: int, body: BoardNodeCreate):
    conn = get_connection()
    _require_board(conn, board_id)
    if body.kind in ("list", "note"):
        if body.ref_id is None:
            raise HTTPException(400, f"ref_id is required for kind='{body.kind}'")
        table = "lists" if body.kind == "list" else "notes"
        if not conn.execute(
            f"SELECT 1 FROM {table} WHERE id = ?", (body.ref_id,)
        ).fetchone():
            raise HTTPException(400, f"ref_id does not exist in {table}")
    cursor = conn.execute(
        """INSERT INTO board_nodes
           (board_id, kind, ref_id, title, body, color, x, y, width, height, z)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            board_id,
            body.kind,
            body.ref_id,
            body.title,
            body.body,
            body.color,
            body.x,
            body.y,
            body.width,
            body.height,
            body.z,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM board_nodes WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_node(row)


@router.patch("/{board_id}/nodes/{node_id}", response_model=BoardNode)
async def update_node(board_id: int, node_id: int, body: BoardNodeUpdate):
    conn = get_connection()
    _require_node(conn, board_id, node_id)
    updates = body.model_dump(exclude_unset=True)
    apply_update(conn, "board_nodes", node_id, updates)
    row = conn.execute(
        "SELECT * FROM board_nodes WHERE id = ?", (node_id,)
    ).fetchone()
    return _row_to_node(row)


@router.delete("/{board_id}/nodes/{node_id}", status_code=204)
async def delete_node(board_id: int, node_id: int):
    conn = get_connection()
    _require_board(conn, board_id)
    conn.execute(
        "DELETE FROM board_nodes WHERE id = ? AND board_id = ?",
        (node_id, board_id),
    )
    conn.commit()


@router.post("/{board_id}/nodes/bulk-positions", status_code=204)
async def bulk_positions(board_id: int, body: BoardNodeBulkPositions):
    conn = get_connection()
    _require_board(conn, board_id)
    try:
        for entry in body.positions:
            conn.execute(
                """UPDATE board_nodes
                      SET x = ?, y = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND board_id = ?""",
                (entry.x, entry.y, entry.id, board_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ── Edges ─────────────────────────────────────────────────────────────────


@router.post("/{board_id}/edges", response_model=BoardEdge, status_code=201)
async def create_edge(board_id: int, body: BoardEdgeCreate):
    conn = get_connection()
    _require_board(conn, board_id)
    if body.source_node_id == body.target_node_id:
        raise HTTPException(400, "source and target must differ (no self-loops)")
    rows = conn.execute(
        "SELECT id FROM board_nodes WHERE id IN (?, ?) AND board_id = ?",
        (body.source_node_id, body.target_node_id, board_id),
    ).fetchall()
    found = {r["id"] for r in rows}
    if body.source_node_id not in found or body.target_node_id not in found:
        raise HTTPException(
            400, "source_node_id and target_node_id must both belong to this board"
        )
    cursor = conn.execute(
        """INSERT INTO board_edges
           (board_id, source_node_id, target_node_id, label, style)
           VALUES (?, ?, ?, ?, ?)""",
        (
            board_id,
            body.source_node_id,
            body.target_node_id,
            body.label,
            body.style,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM board_edges WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_edge(row)


@router.patch("/{board_id}/edges/{edge_id}", response_model=BoardEdge)
async def update_edge(board_id: int, edge_id: int, body: BoardEdgeUpdate):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM board_edges WHERE id = ? AND board_id = ?",
        (edge_id, board_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Edge not found")
    updates = body.model_dump(exclude_unset=True)
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [edge_id]
        conn.execute(
            f"UPDATE board_edges SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
    row = conn.execute(
        "SELECT * FROM board_edges WHERE id = ?", (edge_id,)
    ).fetchone()
    return _row_to_edge(row)


@router.delete("/{board_id}/edges/{edge_id}", status_code=204)
async def delete_edge(board_id: int, edge_id: int):
    conn = get_connection()
    conn.execute(
        "DELETE FROM board_edges WHERE id = ? AND board_id = ?",
        (edge_id, board_id),
    )
    conn.commit()
