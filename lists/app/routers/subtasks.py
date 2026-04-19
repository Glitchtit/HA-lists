"""HA-lists — Subtask CRUD + toggle."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from database import get_connection
from models import Subtask, SubtaskCreate, SubtaskUpdate
from routers._crud import apply_update, coerce_bool_cols

router = APIRouter(prefix="/api/subtasks", tags=["subtasks"])


def _row_to_subtask(row) -> dict:
    return coerce_bool_cols({k: row[k] for k in row.keys()}, "ai_generated")


@router.get("/", response_model=list[Subtask])
async def list_subtasks(item_id: int | None = None):
    conn = get_connection()
    if item_id is None:
        rows = conn.execute("SELECT * FROM subtasks ORDER BY sort_order, id").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM subtasks WHERE item_id = ? ORDER BY sort_order, id",
            (item_id,),
        ).fetchall()
    return [_row_to_subtask(r) for r in rows]


@router.get("/{subtask_id}", response_model=Subtask)
async def get_subtask(subtask_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Subtask not found")
    return _row_to_subtask(row)


@router.post("/", response_model=Subtask, status_code=201)
async def create_subtask(body: SubtaskCreate):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM items WHERE id = ?", (body.item_id,)).fetchone():
        raise HTTPException(400, "item_id does not exist")
    cursor = conn.execute(
        """INSERT INTO subtasks (item_id, title, sort_order, ai_generated)
           VALUES (?, ?, ?, ?)""",
        (body.item_id, body.title, body.sort_order, 1 if body.ai_generated else 0),
    )
    conn.commit()
    return await get_subtask(cursor.lastrowid)


@router.patch("/{subtask_id}", response_model=Subtask)
async def update_subtask(subtask_id: int, body: SubtaskUpdate):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM subtasks WHERE id = ?", (subtask_id,)).fetchone():
        raise HTTPException(404, "Subtask not found")
    updates = body.model_dump(exclude_unset=True)
    # If status flips to completed, stamp completed_at; if back to open, clear it.
    if "status" in updates:
        if updates["status"] == "completed":
            conn.execute(
                "UPDATE subtasks SET completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (subtask_id,),
            )
        else:
            conn.execute(
                "UPDATE subtasks SET completed_at = NULL WHERE id = ?",
                (subtask_id,),
            )
        conn.commit()
    apply_update(conn, "subtasks", subtask_id, updates, touch_updated_at=False)
    return await get_subtask(subtask_id)


@router.post("/{subtask_id}/toggle", response_model=Subtask)
async def toggle_subtask(subtask_id: int):
    conn = get_connection()
    row = conn.execute("SELECT status FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Subtask not found")
    new_status = "open" if row["status"] == "completed" else "completed"
    completed_at = "CURRENT_TIMESTAMP" if new_status == "completed" else "NULL"
    conn.execute(
        f"UPDATE subtasks SET status = ?, completed_at = {completed_at} WHERE id = ?",
        (new_status, subtask_id),
    )
    conn.commit()
    return await get_subtask(subtask_id)


@router.delete("/{subtask_id}", status_code=204)
async def delete_subtask(subtask_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
    conn.commit()
