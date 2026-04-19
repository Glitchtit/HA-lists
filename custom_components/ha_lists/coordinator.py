"""Lists – DataUpdateCoordinator for polling the add-on API."""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)


def _parse_due(due_at: str | None) -> datetime | None:
    if not due_at:
        return None
    try:
        s = due_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


class ListsCoordinator(DataUpdateCoordinator):
    """Fetch data from the Lists add-on API."""

    def __init__(self, hass: HomeAssistant, addon_url: str) -> None:
        super().__init__(hass, _LOGGER, name="Lists", update_interval=SCAN_INTERVAL)
        self.addon_url = addon_url.rstrip("/")

    async def _async_update_data(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                results = await asyncio.gather(
                    client.get(f"{self.addon_url}/api/health"),
                    client.get(f"{self.addon_url}/api/persons/"),
                    client.get(f"{self.addon_url}/api/lists/"),
                    client.get(f"{self.addon_url}/api/items/", params={"status": "open"}),
                    return_exceptions=True,
                )

                for r in results:
                    if isinstance(r, Exception):
                        raise r

                health_resp, persons_resp, lists_resp, items_resp = results

                health = health_resp.json() if health_resp.status_code == 200 else {}
                persons = persons_resp.json() if persons_resp.status_code == 200 else []
                lists = lists_resp.json() if lists_resp.status_code == 200 else []
                items = items_resp.json() if items_resp.status_code == 200 else []

                now = datetime.now(timezone.utc)
                overdue = []
                for it in items:
                    due = _parse_due(it.get("due_at"))
                    if due and due < now:
                        overdue.append(it)

                return {
                    "health": health,
                    "persons": persons,
                    "lists": lists,
                    "items": items,
                    "overdue": overdue,
                    "overdue_count": len(overdue),
                    "open_count": len(items),
                }
        except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
            raise UpdateFailed(
                f"Cannot connect to Lists add-on at {self.addon_url}. "
                f"Check the URL in the integration settings. Error: {exc}"
            ) from exc
        except Exception as exc:
            raise UpdateFailed(f"Error fetching lists data: {exc}") from exc
