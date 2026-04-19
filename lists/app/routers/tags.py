"""HA-lists — Tag CRUD (tags are attached to items via /api/items/:id/tags/:name)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from database import get_connection
from models import Tag, TagCreate, TagUpdate
from routers._crud import apply_update

router = APIRouter(prefix="/api/tags", tags=["tags"])


def _row_to_tag(row) -> dict:
    return {k: row[k] for k in row.keys()}


@router.get("/", response_model=list[Tag])
async def list_tags():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tags ORDER BY name").fetchall()
    return [_row_to_tag(r) for r in rows]


@router.get("/{tag_id}", response_model=Tag)
async def get_tag(tag_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Tag not found")
    return _row_to_tag(row)


@router.post("/", response_model=Tag, status_code=201)
async def create_tag(body: TagCreate):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO tags (name, color) VALUES (?, ?)",
            (body.name, body.color),
        )
        conn.commit()
    except Exception:
        raise HTTPException(409, "Tag name already exists")
    return await get_tag(cursor.lastrowid)


@router.patch("/{tag_id}", response_model=Tag)
async def update_tag(tag_id: int, body: TagUpdate):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM tags WHERE id = ?", (tag_id,)).fetchone():
        raise HTTPException(404, "Tag not found")
    updates = body.model_dump(exclude_unset=True)
    try:
        apply_update(conn, "tags", tag_id, updates, touch_updated_at=False)
    except Exception as exc:
        # SQLite UNIQUE constraint collision on the `name` column.
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(409, "Tag name already exists") from exc
        raise
    return await get_tag(tag_id)


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(tag_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()
