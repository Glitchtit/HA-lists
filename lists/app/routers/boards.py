"""HA-lists — Boards (canvas/whiteboard) CRUD + nodes + edges."""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import re
import shutil
import sqlite3
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

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
    BoardNodeTranslate,
    BoardNodeUpdate,
    BoardUpdate,
    ViewportUpdate,
)
from routers._crud import apply_update, coerce_bool_cols
from routers._duplicate import duplicate_board

router = APIRouter(prefix="/api/boards", tags=["boards"])

logger = logging.getLogger(__name__)

DEFAULT_VIEWPORT = {"x": 0, "y": 0, "zoom": 1}

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MiB — conservative cap for the add-on FS
_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _media_root() -> str:
    # Read DATA_DIR at call time so tests can monkeypatch it.
    return os.path.join(os.environ.get("DATA_DIR", "/data"), "board_media")


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


def _board_media_dir(board_id: int) -> str:
    return os.path.join(_media_root(), str(board_id))


def _media_path(board_id: int, filename: str) -> str:
    # Callers must validate the filename against _SAFE_FILENAME_RE first.
    return os.path.join(_board_media_dir(board_id), filename)


def _validate_parent_group(
    conn: sqlite3.Connection,
    board_id: int,
    parent_group_id: int | None,
    *,
    child_node_id: int | None = None,
) -> None:
    """Raise if `parent_group_id` is invalid for this board / would form a cycle.

    ``child_node_id`` is the node being parented — may be None when creating.
    Walks the parent chain up from `parent_group_id`; if the walk ever lands on
    `child_node_id`, we'd form a cycle. Depth is bounded as a safety net.
    """
    if parent_group_id is None:
        return
    row = conn.execute(
        "SELECT id, kind, board_id, parent_group_id FROM board_nodes WHERE id = ?",
        (parent_group_id,),
    ).fetchone()
    if not row or row["board_id"] != board_id:
        raise HTTPException(400, "parent_group_id must belong to this board")
    if row["kind"] != "group":
        raise HTTPException(400, "parent_group_id must refer to a group node")
    if child_node_id is not None and row["id"] == child_node_id:
        raise HTTPException(400, "a node cannot be its own parent group")
    # Walk ancestors to detect cycles (only relevant when child is itself a group).
    current = row["parent_group_id"]
    for _ in range(64):
        if current is None:
            return
        if child_node_id is not None and current == child_node_id:
            raise HTTPException(400, "parenting would create a cycle")
        nxt = conn.execute(
            "SELECT parent_group_id FROM board_nodes WHERE id = ?", (current,)
        ).fetchone()
        if not nxt:
            return
        current = nxt["parent_group_id"]


def _purge_media_if_orphan(
    conn: sqlite3.Connection, board_id: int, filename: str
) -> None:
    row = conn.execute(
        "SELECT 1 FROM board_nodes WHERE board_id = ? AND media_filename = ? LIMIT 1",
        (board_id, filename),
    ).fetchone()
    if row:
        return  # still referenced by at least one node
    path = _media_path(board_id, filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as exc:
        logger.warning("Could not remove orphan media %s: %s", path, exc)


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

    board_ref_ids = [n["ref_id"] for n in nodes if n["kind"] == "board" and n["ref_id"]]
    board_info: dict[int, dict] = {}
    if board_ref_ids:
        placeholders = ",".join("?" * len(board_ref_ids))
        rows = conn.execute(
            f"""SELECT b.id, b.name, b.icon, b.color, b.updated_at,
                       (SELECT COUNT(*) FROM board_nodes WHERE board_id = b.id) AS node_count,
                       (SELECT COUNT(*) FROM board_edges WHERE board_id = b.id) AS edge_count
                  FROM boards b
                 WHERE b.id IN ({placeholders})""",
            board_ref_ids,
        ).fetchall()
        for r in rows:
            board_info[r["id"]] = {
                "id": r["id"],
                "name": r["name"],
                "icon": r["icon"],
                "color": r["color"],
                "node_count": int(r["node_count"] or 0),
                "edge_count": int(r["edge_count"] or 0),
                "last_modified": r["updated_at"],
            }

    summaries: dict[int, dict | None] = {}
    for n in nodes:
        if n["kind"] == "list":
            summaries[n["id"]] = list_info.get(n["ref_id"]) if n["ref_id"] else None
        elif n["kind"] == "note":
            summaries[n["id"]] = note_info.get(n["ref_id"]) if n["ref_id"] else None
        elif n["kind"] == "board":
            summaries[n["id"]] = board_info.get(n["ref_id"]) if n["ref_id"] else None
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
    media_dir = _board_media_dir(board_id)
    if os.path.isdir(media_dir):
        try:
            shutil.rmtree(media_dir)
        except OSError as exc:
            logger.warning("Could not remove media dir %s: %s", media_dir, exc)


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
    if body.kind == "board":
        if body.ref_id is None:
            raise HTTPException(400, "ref_id is required for kind='board'")
        if body.ref_id == board_id:
            raise HTTPException(400, "a board cannot portal to itself")
        if not conn.execute(
            "SELECT 1 FROM boards WHERE id = ?", (body.ref_id,)
        ).fetchone():
            raise HTTPException(400, "ref_id does not exist in boards")
    if body.kind in ("image", "file"):
        if not body.media_filename:
            raise HTTPException(400, f"media_filename is required for kind='{body.kind}'")
        if not _SAFE_FILENAME_RE.match(body.media_filename):
            raise HTTPException(400, "media_filename contains invalid characters")
        if not os.path.exists(_media_path(board_id, body.media_filename)):
            raise HTTPException(400, "media_filename does not exist on disk")
    _validate_parent_group(conn, board_id, body.parent_group_id)
    cursor = conn.execute(
        """INSERT INTO board_nodes
           (board_id, kind, ref_id, title, body, color, x, y, width, height, z,
            media_filename, media_mime, media_size, media_alt, parent_group_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            body.media_filename,
            body.media_mime,
            body.media_size,
            body.media_alt,
            body.parent_group_id,
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
    if "parent_group_id" in updates:
        _validate_parent_group(
            conn, board_id, updates["parent_group_id"], child_node_id=node_id
        )
    apply_update(conn, "board_nodes", node_id, updates)
    row = conn.execute(
        "SELECT * FROM board_nodes WHERE id = ?", (node_id,)
    ).fetchone()
    return _row_to_node(row)


@router.delete("/{board_id}/nodes/{node_id}", status_code=204)
async def delete_node(board_id: int, node_id: int):
    conn = get_connection()
    _require_board(conn, board_id)
    row = conn.execute(
        "SELECT kind, media_filename FROM board_nodes WHERE id = ? AND board_id = ?",
        (node_id, board_id),
    ).fetchone()
    conn.execute(
        "DELETE FROM board_nodes WHERE id = ? AND board_id = ?",
        (node_id, board_id),
    )
    conn.commit()
    if row and row["kind"] in ("image", "file") and row["media_filename"]:
        _purge_media_if_orphan(conn, board_id, row["media_filename"])


@router.post("/{board_id}/nodes/{group_id}/translate", status_code=204)
async def translate_group(
    board_id: int, group_id: int, body: BoardNodeTranslate
):
    """Move a group and every descendant by (dx, dy) in a single transaction.

    The endpoint is idempotent only in the sense that repeated calls compound —
    callers should pass the cumulative delta since the last drag started.
    """
    conn = get_connection()
    row = _require_node(conn, board_id, group_id)
    if row["kind"] != "group":
        raise HTTPException(400, "node is not a group")
    # BFS across the parent chain to collect all descendants, then the group itself.
    descendants: list[int] = []
    frontier: list[int] = [group_id]
    seen: set[int] = {group_id}
    while frontier:
        placeholders = ",".join("?" * len(frontier))
        children = conn.execute(
            f"SELECT id FROM board_nodes "
            f"WHERE board_id = ? AND parent_group_id IN ({placeholders})",
            [board_id, *frontier],
        ).fetchall()
        frontier = []
        for c in children:
            cid = c["id"]
            if cid in seen:
                continue
            seen.add(cid)
            descendants.append(cid)
            frontier.append(cid)
    try:
        conn.execute(
            """UPDATE board_nodes
                  SET x = x + ?, y = y + ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND board_id = ?""",
            (body.dx, body.dy, group_id, board_id),
        )
        if descendants:
            placeholders = ",".join("?" * len(descendants))
            conn.execute(
                f"""UPDATE board_nodes
                       SET x = x + ?, y = y + ?, updated_at = CURRENT_TIMESTAMP
                     WHERE board_id = ? AND id IN ({placeholders})""",
                [body.dx, body.dy, board_id, *descendants],
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


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


# ── Attachments ────────────────────────────────────────────────────────────


@router.post("/{board_id}/attachments", status_code=201)
async def upload_attachment(board_id: int, file: UploadFile):
    """Store an uploaded file under /{DATA_DIR}/board_media/{board_id}/ and
    return metadata the client can use to create an image/file node.
    The response's `filename` must be round-tripped into
    POST /{board_id}/nodes with kind=image|file."""
    conn = get_connection()
    _require_board(conn, board_id)

    ext = ""
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext and not re.match(r"^\.[A-Za-z0-9]{1,8}$", ext):
            ext = ""
    stored_name = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(_board_media_dir(board_id), exist_ok=True)
    path = _media_path(board_id, stored_name)

    total = 0
    try:
        with open(path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    out.close()
                    os.remove(path)
                    raise HTTPException(
                        413, f"file exceeds {MAX_UPLOAD_BYTES} bytes"
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        raise HTTPException(500, f"upload failed: {exc}")

    mime = file.content_type or mimetypes.guess_type(file.filename or stored_name)[0] \
        or "application/octet-stream"
    return {
        "filename": stored_name,
        "original_name": file.filename or "",
        "mime": mime,
        "size": total,
    }


@router.get("/{board_id}/attachments/{filename}")
async def serve_attachment(board_id: int, filename: str):
    if not _SAFE_FILENAME_RE.match(filename):
        raise HTTPException(400, "invalid filename")
    conn = get_connection()
    # Tombstone protection: only serve files still referenced by a node.
    ref = conn.execute(
        "SELECT 1 FROM board_nodes WHERE board_id = ? AND media_filename = ? LIMIT 1",
        (board_id, filename),
    ).fetchone()
    if not ref:
        raise HTTPException(404, "attachment not found")
    path = _media_path(board_id, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "attachment not found")
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(path, media_type=mime)
