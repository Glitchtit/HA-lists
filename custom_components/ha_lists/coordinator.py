"""Lists – DataUpdateCoordinator for polling the add-on API."""

from __future__ import annotations
import asyncio
import logging
import datetime as dt
from datetime import timedelta

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import get_default_context

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)


def _parse_due(value: str | None) -> dt.date | dt.datetime | None:
    """The add-on stores due_at as an ISO date ("2026-10-20") or a local datetime ("2026-10-20T18:00")."""
    if not value:
        return None
    if "T" not in value:
        return dt_util.parse_date(value)
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_util.get_default_time_zone())


def _is_overdue(due: dt.date | dt.datetime | None, now: dt.datetime) -> bool:
    """A timed item is overdue once its time has passed, a date-only item from the next day."""
    if isinstance(due, dt.datetime):
        return due < now
    return due is not None and due < now.date()


class ListsCoordinator(DataUpdateCoordinator):
    """Fetch data from the Lists add-on API."""

    def __init__(self, hass: HomeAssistant, addon_url: str) -> None:
        super().__init__(hass, _LOGGER, name="Lists", update_interval=SCAN_INTERVAL)
        self.addon_url = addon_url.rstrip("/")

    async def _async_update_data(self) -> dict:
        try:
            async with httpx.AsyncClient(verify=get_default_context(), timeout=15) as client:
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

                now = dt_util.now()
                overdue = [it for it in items if _is_overdue(_parse_due(it.get("due_at")), now)]

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
