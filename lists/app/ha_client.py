"""HA-lists — Home Assistant Supervisor API client.

Minimal surface for Phase 1: timezone + person listing. Notification plumbing
and todo/calendar writes will arrive in later phases.
"""

from __future__ import annotations
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
SUPERVISOR_URL = "http://supervisor"
HA_URL = "http://supervisor/core"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


async def get_ha_timezone() -> str | None:
    """Fetch the Home Assistant timezone from the Supervisor."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{SUPERVISOR_URL}/core/api/config",
                headers=_headers(),
            )
            resp.raise_for_status()
            return resp.json().get("time_zone")
    except Exception as e:
        logger.warning("Could not fetch HA timezone: %s", e)
        return None


async def get_persons() -> list[dict]:
    """Fetch person entities from Home Assistant."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{HA_URL}/api/states",
                headers=_headers(),
            )
            resp.raise_for_status()
            states = resp.json()
            persons: list[dict] = []
            for s in states:
                if s.get("entity_id", "").startswith("person."):
                    attrs = s.get("attributes", {})
                    persons.append({
                        "entity_id": s["entity_id"],
                        "name": attrs.get("friendly_name", s["entity_id"]),
                        "avatar_url": attrs.get("entity_picture", ""),
                        "user_id": attrs.get("user_id", "") or "",
                    })
            return persons
    except Exception as e:
        logger.error("Failed to fetch persons from HA: %s", e)
        return []
