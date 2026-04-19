"""Shared CRUD helpers — dynamic UPDATE builder + row coercion."""

from __future__ import annotations
import sqlite3
from typing import Any


def apply_update(
    conn: sqlite3.Connection,
    table: str,
    row_id: int,
    fields: dict[str, Any],
    *,
    touch_updated_at: bool = True,
    id_column: str = "id",
) -> None:
    """Apply a partial update. Pass only fields the user set."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    if touch_updated_at:
        set_clause += ", updated_at = CURRENT_TIMESTAMP"
    values = list(fields.values()) + [row_id]
    conn.execute(
        f"UPDATE {table} SET {set_clause} WHERE {id_column} = ?",
        values,
    )
    conn.commit()


def coerce_bool_cols(row: dict, *cols: str) -> dict:
    """SQLite stores booleans as INTEGER; convert back for pydantic."""
    for c in cols:
        if c in row and row[c] is not None:
            row[c] = bool(row[c])
    return row
