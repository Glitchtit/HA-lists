"""HA-lists — Note templates CRUD + variable substitution for new notes."""

from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, HTTPException

from database import get_connection
from models import Note, NoteTemplate, NoteTemplateCreate, NoteTemplateUpdate
from routers._crud import apply_update, coerce_bool_cols

router = APIRouter(prefix="/api/note-templates", tags=["note-templates"])


_VAR_RE = re.compile(r"\{\{\s*(date|time|title|datetime)(?:\s*:\s*([^}]+))?\s*\}\}")


def render_template_text(text: str, *, title: str = "") -> str:
    """Substitute ``{{date}}``, ``{{time}}``, ``{{title}}``, and the
    parameterised ``{{date:FORMAT}}`` / ``{{datetime:FORMAT}}`` variables in
    ``text``. FORMAT is a Python ``strftime`` string. Unknown variables and
    bad formats fall back to ``str(now)`` / the literal title so a template
    that references a future variable never fails outright.
    """
    if not text:
        return text
    now = datetime.now()

    def _sub(m: re.Match[str]) -> str:
        var = m.group(1)
        fmt = (m.group(2) or "").strip()
        if var == "title":
            return title
        if var == "time":
            return now.strftime(fmt) if fmt else now.strftime("%H:%M")
        if var == "datetime":
            return now.strftime(fmt) if fmt else now.strftime("%Y-%m-%d %H:%M")
        # date (default)
        try:
            return now.strftime(fmt) if fmt else now.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return now.strftime("%Y-%m-%d")

    return _VAR_RE.sub(_sub, text)


def _row(r) -> dict:
    return coerce_bool_cols({k: r[k] for k in r.keys()}, "is_system")


@router.get("/", response_model=list[NoteTemplate])
async def list_templates(category: str | None = None):
    conn = get_connection()
    sql = "SELECT * FROM note_templates"
    params: list = []
    if category:
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY is_system DESC, sort_order, name"
    return [_row(r) for r in conn.execute(sql, params).fetchall()]


@router.get("/{tid}", response_model=NoteTemplate)
async def get_template(tid: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM note_templates WHERE id = ?", (tid,)).fetchone()
    if not row:
        raise HTTPException(404, "Template not found")
    return _row(row)


@router.post("/", response_model=NoteTemplate, status_code=201)
async def create_template(body: NoteTemplateCreate):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO note_templates
             (name, icon, title_tpl, body_md, category, is_system, sort_order)
           VALUES (?, ?, ?, ?, ?, 0, ?)""",
        (body.name, body.icon, body.title_tpl, body.body_md, body.category, body.sort_order),
    )
    conn.commit()
    return await get_template(cur.lastrowid)


@router.patch("/{tid}", response_model=NoteTemplate)
async def update_template(tid: int, body: NoteTemplateUpdate):
    conn = get_connection()
    row = conn.execute(
        "SELECT is_system FROM note_templates WHERE id = ?", (tid,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Template not found")
    if row["is_system"]:
        raise HTTPException(403, "System templates are read-only")
    updates = body.model_dump(exclude_unset=True)
    apply_update(conn, "note_templates", tid, updates)
    return await get_template(tid)


@router.delete("/{tid}", status_code=204)
async def delete_template(tid: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT is_system FROM note_templates WHERE id = ?", (tid,)
    ).fetchone()
    if not row:
        return
    if row["is_system"]:
        raise HTTPException(403, "System templates are read-only")
    conn.execute("DELETE FROM note_templates WHERE id = ?", (tid,))
    conn.commit()


@router.post("/{tid}/apply", response_model=Note, status_code=201)
async def apply_template(tid: int, payload: dict | None = None):
    """Create a new note from template ``tid``.

    Optional payload: ``{"folder_id": int, "title": str}``. ``title`` overrides
    the template's ``title_tpl``; if both are empty the title falls back to
    the template name. Variable substitution runs on both title and body.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM note_templates WHERE id = ?", (tid,)).fetchone()
    if not row:
        raise HTTPException(404, "Template not found")

    folder_id = None
    requested_title = ""
    if payload:
        folder_id = payload.get("folder_id")
        requested_title = (payload.get("title") or "").strip()

    if folder_id is not None and not conn.execute(
        "SELECT 1 FROM folders WHERE id = ?", (folder_id,)
    ).fetchone():
        raise HTTPException(400, "folder_id does not exist")

    base_title = requested_title or row["title_tpl"] or row["name"]
    rendered_title = render_template_text(base_title, title=base_title) or "Untitled note"
    rendered_body = render_template_text(row["body_md"] or "", title=rendered_title)

    # Defer to notes router so wikilinks in the body get indexed.
    from routers.notes import _sync_links, get_note as _get_note
    cur = conn.execute(
        """INSERT INTO notes (folder_id, title, body, icon, color, pinned, sort_order)
           VALUES (?, ?, ?, ?, '', 0, 0)""",
        (folder_id, rendered_title, rendered_body, row["icon"] or "📝"),
    )
    note_id = cur.lastrowid
    _sync_links(conn, note_id, rendered_body)
    conn.commit()
    return await _get_note(note_id)
