"""HA-lists — Item CRUD + completion."""

from __future__ import annotations
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import get_connection
from models import Item, ItemCreate, ItemUpdate
from routers._crud import apply_update
from routers._duplicate import duplicate_item


class ItemDuplicateBody(BaseModel):
    target_list_id: int | None = None

router = APIRouter(prefix="/api/items", tags=["items"])


def _row_to_item(row, tags: list[str] | None = None) -> dict:
    out = {k: row[k] for k in row.keys()}
    out["tags"] = tags or []
    return out


def _load_tags(conn, item_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT t.name FROM tags t
           JOIN item_tags it ON it.tag_id = t.id
           WHERE it.item_id = ?
           ORDER BY t.name""",
        (item_id,),
    ).fetchall()
    return [r["name"] for r in rows]


@router.get("/", response_model=list[Item])
async def list_items(
    list_id: int | None = None,
    assigned_to: str | None = None,
    status: Literal["open", "completed", "archived"] | None = None,
    tag: str | None = Query(None, description="Filter by tag name"),
):
    conn = get_connection()
    clauses: list[str] = []
    params: list = []
    if list_id is not None:
        clauses.append("i.list_id = ?")
        params.append(list_id)
    if assigned_to is not None:
        clauses.append("i.assigned_to = ?")
        params.append(assigned_to)
    if status is not None:
        clauses.append("i.status = ?")
        params.append(status)
    if tag is not None:
        clauses.append(
            "i.id IN (SELECT it.item_id FROM item_tags it "
            "JOIN tags t ON t.id = it.tag_id WHERE t.name = ?)"
        )
        params.append(tag)
    sql = "SELECT i.* FROM items i"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY i.sort_order, i.created_at"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_item(r, _load_tags(conn, r["id"])) for r in rows]


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Item not found")
    return _row_to_item(row, _load_tags(conn, item_id))


@router.post("/", response_model=Item, status_code=201)
async def create_item(body: ItemCreate):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM lists WHERE id = ?", (body.list_id,)).fetchone():
        raise HTTPException(400, "list_id does not exist")
    if body.assigned_to and not conn.execute(
        "SELECT 1 FROM persons WHERE entity_id = ?", (body.assigned_to,)
    ).fetchone():
        raise HTTPException(400, "assigned_to does not match a known person")
    cursor = conn.execute(
        """INSERT INTO items
           (list_id, title, notes, assigned_to, due_at, priority,
            estimate_min, estimate_max, spiciness, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            body.list_id, body.title, body.notes, body.assigned_to, body.due_at,
            body.priority, body.estimate_min, body.estimate_max, body.spiciness,
            body.sort_order,
        ),
    )
    conn.commit()
    return await get_item(cursor.lastrowid)


@router.patch("/{item_id}", response_model=Item)
async def update_item(item_id: int, body: ItemUpdate):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
        raise HTTPException(404, "Item not found")
    updates = body.model_dump(exclude_unset=True)
    if "list_id" in updates and updates["list_id"] is not None:
        if not conn.execute(
            "SELECT 1 FROM lists WHERE id = ?", (updates["list_id"],)
        ).fetchone():
            raise HTTPException(400, "list_id does not exist")
    if "assigned_to" in updates and updates["assigned_to"] is not None:
        if not conn.execute(
            "SELECT 1 FROM persons WHERE entity_id = ?", (updates["assigned_to"],)
        ).fetchone():
            raise HTTPException(400, "assigned_to does not match a known person")
    apply_update(conn, "items", item_id, updates)
    return await get_item(item_id)


@router.post("/{item_id}/complete", response_model=Item)
async def complete_item(item_id: int, completed_by: str | None = None):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
        raise HTTPException(404, "Item not found")
    conn.execute(
        """UPDATE items
           SET status = 'completed',
               completed_at = CURRENT_TIMESTAMP,
               completed_by = ?,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (completed_by, item_id),
    )
    conn.commit()
    return await get_item(item_id)


@router.post("/{item_id}/reopen", response_model=Item)
async def reopen_item(item_id: int):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
        raise HTTPException(404, "Item not found")
    conn.execute(
        """UPDATE items
           SET status = 'open', completed_at = NULL, completed_by = NULL,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (item_id,),
    )
    conn.commit()
    return await get_item(item_id)


@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()


@router.post("/{item_id}/duplicate", response_model=Item, status_code=201)
async def duplicate_item_endpoint(item_id: int, body: ItemDuplicateBody | None = None):
    """Deep-copy an item (+ subtasks + tag links), optionally into another list."""
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
        raise HTTPException(404, "Item not found")
    body = body or ItemDuplicateBody()
    if body.target_list_id is not None and not conn.execute(
        "SELECT 1 FROM lists WHERE id = ?", (body.target_list_id,)
    ).fetchone():
        raise HTTPException(400, "target_list_id does not exist")
    new_id = duplicate_item(conn, item_id, target_list_id=body.target_list_id)
    return await get_item(new_id)


# ── Tag attachment ───────────────────────────────────────────────────────────


@router.post("/{item_id}/tags/{tag_name}", response_model=Item)
async def attach_tag(item_id: int, tag_name: str):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
        raise HTTPException(404, "Item not found")
    tag = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
    if not tag:
        cursor = conn.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
        tag_id = cursor.lastrowid
    else:
        tag_id = tag["id"]
    conn.execute(
        "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
        (item_id, tag_id),
    )
    conn.commit()
    return await get_item(item_id)


@router.delete("/{item_id}/tags/{tag_name}", response_model=Item)
async def detach_tag(item_id: int, tag_name: str):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
        raise HTTPException(404, "Item not found")
    conn.execute(
        """DELETE FROM item_tags
           WHERE item_id = ?
             AND tag_id = (SELECT id FROM tags WHERE name = ?)""",
        (item_id, tag_name),
    )
    conn.commit()
    return await get_item(item_id)
