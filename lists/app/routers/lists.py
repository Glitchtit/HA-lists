"""HA-lists — List CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection
from models import List_, ListCreate, ListUpdate
from routers._crud import apply_update, coerce_bool_cols
from routers._duplicate import duplicate_list


class ListDuplicateBody(BaseModel):
    target_folder_id: int | None = None
    keep_folder: bool = True  # when True (default), ignore target_folder_id


router = APIRouter(prefix="/api/lists", tags=["lists"])


def _row_to_list(row) -> dict:
    return coerce_bool_cols({k: row[k] for k in row.keys()}, "archived")


@router.get("/", response_model=list[List_])
async def list_lists(folder_id: int | None = None, include_archived: bool = False):
    conn = get_connection()
    clauses = []
    params: list = []
    if folder_id is not None:
        clauses.append("folder_id = ?")
        params.append(folder_id)
    if not include_archived:
        clauses.append("archived = 0")
    sql = "SELECT * FROM lists"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY sort_order, name"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_list(r) for r in rows]


@router.get("/{list_id}", response_model=List_)
async def get_list(list_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM lists WHERE id = ?", (list_id,)).fetchone()
    if not row:
        raise HTTPException(404, "List not found")
    return _row_to_list(row)


@router.post("/", response_model=List_, status_code=201)
async def create_list(body: ListCreate):
    conn = get_connection()
    if body.folder_id is not None:
        if not conn.execute("SELECT 1 FROM folders WHERE id = ?", (body.folder_id,)).fetchone():
            raise HTTPException(400, "folder_id does not exist")
    cursor = conn.execute(
        "INSERT INTO lists (folder_id, name, icon, color, sort_order) VALUES (?, ?, ?, ?, ?)",
        (body.folder_id, body.name, body.icon, body.color, body.sort_order),
    )
    conn.commit()
    return await get_list(cursor.lastrowid)


@router.patch("/{list_id}", response_model=List_)
async def update_list(list_id: int, body: ListUpdate):
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM lists WHERE id = ?", (list_id,)).fetchone():
        raise HTTPException(404, "List not found")
    updates: dict = {}
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "archived":
            updates[k] = 1 if v else 0
        elif k == "folder_id" and v is not None:
            if not conn.execute("SELECT 1 FROM folders WHERE id = ?", (v,)).fetchone():
                raise HTTPException(400, "folder_id does not exist")
            updates[k] = v
        else:
            updates[k] = v
    apply_update(conn, "lists", list_id, updates)
    return await get_list(list_id)


@router.delete("/{list_id}", status_code=204)
async def delete_list(list_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
    conn.commit()


@router.post("/{list_id}/duplicate", response_model=List_, status_code=201)
async def duplicate_list_endpoint(list_id: int, body: ListDuplicateBody | None = None):
    """Deep-copy a list (+ all items + their subtasks + tag links).

    Body options:
      - ``keep_folder=true`` (default): copy lands in the source folder.
      - ``keep_folder=false``: copy lands in ``target_folder_id`` (``null`` = Unfiled).
    """
    conn = get_connection()
    if not conn.execute("SELECT 1 FROM lists WHERE id = ?", (list_id,)).fetchone():
        raise HTTPException(404, "List not found")

    body = body or ListDuplicateBody()
    if body.keep_folder:
        new_id = duplicate_list(conn, list_id)
    else:
        if body.target_folder_id is not None and not conn.execute(
            "SELECT 1 FROM folders WHERE id = ?", (body.target_folder_id,)
        ).fetchone():
            raise HTTPException(400, "target_folder_id does not exist")
        new_id = duplicate_list(conn, list_id, target_folder_id=body.target_folder_id)
    return await get_list(new_id)
