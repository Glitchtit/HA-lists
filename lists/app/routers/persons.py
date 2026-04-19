"""HA-lists — Person management (synced from Home Assistant).

Persons are a read-mostly mirror of HA's `person.*` entities: the HA-lists DB
is the authoritative store for *which* persons the app knows about, but names
and avatars flow one-way from HA. A manual POST /sync and a 6-hour periodic
refresh keep the mirror fresh.
"""

from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

import ha_client
from database import get_connection
from models import Person

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/persons", tags=["persons"])


def _row_to_person(row) -> dict:
    out = {k: row[k] for k in row.keys()}
    out["active"] = bool(out.get("active", 1))
    return out


async def sync_persons_from_ha() -> list[dict]:
    """Upsert persons from HA, and deactivate ones HA no longer exposes.

    We soft-deactivate (active=0) rather than delete so that items previously
    assigned to a person still resolve cleanly via FK.
    """
    ha_persons = await ha_client.get_persons()
    conn = get_connection()
    for p in ha_persons:
        conn.execute(
            """INSERT INTO persons (entity_id, name, avatar_url, ha_user_id, active)
               VALUES (?, ?, ?, ?, 1)
               ON CONFLICT(entity_id) DO UPDATE SET
                   name       = excluded.name,
                   avatar_url = excluded.avatar_url,
                   ha_user_id = excluded.ha_user_id,
                   active     = 1""",
            (p["entity_id"], p["name"], p.get("avatar_url", ""), p.get("user_id", "")),
        )
    if ha_persons:
        ha_ids = [p["entity_id"] for p in ha_persons]
        placeholders = ",".join("?" * len(ha_ids))
        conn.execute(
            f"UPDATE persons SET active = 0 WHERE entity_id NOT IN ({placeholders})",
            ha_ids,
        )
    else:
        conn.execute("UPDATE persons SET active = 0")
    conn.commit()
    return ha_persons


@router.get("/me", response_model=Optional[Person])
async def whoami(request: Request):
    """Return the person matching the current HA user, or null if not found."""
    ha_user_id = request.headers.get("X-Remote-User-Id", "")
    if not ha_user_id:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM persons WHERE ha_user_id = ?", (ha_user_id,)
    ).fetchone()
    if row:
        return _row_to_person(row)
    # Not found — re-sync once (covers cases where the HA user_id was empty
    # on first boot and only got populated after a person link was confirmed).
    try:
        await sync_persons_from_ha()
        row = conn.execute(
            "SELECT * FROM persons WHERE ha_user_id = ?", (ha_user_id,)
        ).fetchone()
    except Exception as e:
        logger.warning("Re-sync from /me failed: %s", e)
    return _row_to_person(row) if row else None


@router.get("/", response_model=list[Person])
async def list_persons(include_inactive: bool = False):
    conn = get_connection()
    if include_inactive:
        rows = conn.execute("SELECT * FROM persons ORDER BY name").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM persons WHERE active = 1 ORDER BY name"
        ).fetchall()
    return [_row_to_person(r) for r in rows]


@router.get("/{entity_id}", response_model=Person)
async def get_person(entity_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM persons WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Person not found")
    return _row_to_person(row)


@router.post("/sync", response_model=list[Person])
async def sync_persons():
    """Force a re-sync from Home Assistant."""
    await sync_persons_from_ha()
    return await list_persons()
