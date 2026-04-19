"""HA-lists — Folder CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from database import get_connection
from models import Folder, FolderCreate, FolderUpdate
from routers._crud import apply_update, coerce_bool_cols
from routers._duplicate import duplicate_folder

router = APIRouter(prefix="/api/folders", tags=["folders"])


def _row_to_folder(row) -> dict:
    return coerce_bool_cols({k: row[k] for k in row.keys()}, "archived")


@router.get("/", response_model=list[Folder])
async def list_folders(include_archived: bool = False):
    conn = get_connection()
    sql = "SELECT * FROM folders"
    if not include_archived:
        sql += " WHERE archived = 0"
    sql += " ORDER BY sort_order, name"
    rows = conn.execute(sql).fetchall()
    return [_row_to_folder(r) for r in rows]


@router.get("/{folder_id}", response_model=Folder)
async def get_folder(folder_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Folder not found")
    return _row_to_folder(row)


@router.post("/", response_model=Folder, status_code=201)
async def create_folder(body: FolderCreate):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO folders (name, icon, color, sort_order) VALUES (?, ?, ?, ?)",
        (body.name, body.icon, body.color, body.sort_order),
    )
    conn.commit()
    return await get_folder(cursor.lastrowid)


@router.patch("/{folder_id}", response_model=Folder)
async def update_folder(folder_id: int, body: FolderUpdate):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM folders WHERE id = ?", (folder_id,)).fetchone():
        raise HTTPException(404, "Folder not found")
    updates = {
        k: (1 if v else 0) if k == "archived" else v
        for k, v in body.model_dump(exclude_unset=True).items()
    }
    apply_update(conn, "folders", folder_id, updates)
    return await get_folder(folder_id)


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(folder_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
    conn.commit()


@router.post("/{folder_id}/duplicate", response_model=Folder, status_code=201)
async def duplicate_folder_endpoint(folder_id: int):
    """Deep-copy the folder and everything it contains (lists, items, subtasks, tag links)."""
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM folders WHERE id = ?", (folder_id,)).fetchone():
        raise HTTPException(404, "Folder not found")
    new_id = duplicate_folder(conn, folder_id)
    return await get_folder(new_id)
