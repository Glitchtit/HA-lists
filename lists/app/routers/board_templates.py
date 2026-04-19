"""HA-lists — Board templates (card presets for quick capture)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException

from database import get_connection
from models import BoardTemplate, BoardTemplateCreate, BoardTemplateUpdate
from routers._crud import apply_update, coerce_bool_cols

router = APIRouter(prefix="/api/board-templates", tags=["board-templates"])


def _row(r: sqlite3.Row) -> dict:
    return coerce_bool_cols({k: r[k] for k in r.keys()}, "is_system")


@router.get("/", response_model=list[BoardTemplate])
async def list_templates(category: str | None = None):
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT * FROM board_templates WHERE category = ? ORDER BY is_system DESC, sort_order, id",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM board_templates ORDER BY is_system DESC, sort_order, id"
        ).fetchall()
    return [_row(r) for r in rows]


@router.get("/{template_id}", response_model=BoardTemplate)
async def get_template(template_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM board_templates WHERE id = ?", (template_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Template not found")
    return _row(row)


@router.post("/", response_model=BoardTemplate, status_code=201)
async def create_template(payload: BoardTemplateCreate):
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO board_templates
             (name, icon, color, body_md, title, width, height, category, is_system)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (
            payload.name, payload.icon, payload.color, payload.body_md,
            payload.title, payload.width, payload.height, payload.category,
        ),
    )
    conn.commit()
    return await get_template(cursor.lastrowid)


@router.patch("/{template_id}", response_model=BoardTemplate)
async def update_template(template_id: int, patch: BoardTemplateUpdate):
    conn = get_connection()
    row = conn.execute(
        "SELECT is_system FROM board_templates WHERE id = ?", (template_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Template not found")
    if row["is_system"]:
        raise HTTPException(403, "System templates are read-only")
    apply_update(conn, "board_templates", template_id, patch.model_dump(exclude_unset=True))
    conn.commit()
    return await get_template(template_id)


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT is_system FROM board_templates WHERE id = ?", (template_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Template not found")
    if row["is_system"]:
        raise HTTPException(403, "System templates are read-only")
    conn.execute("DELETE FROM board_templates WHERE id = ?", (template_id,))
    conn.commit()
