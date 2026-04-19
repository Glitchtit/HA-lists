"""Lists – Calendar entity showing items with due_at."""

from __future__ import annotations
from datetime import datetime, timezone

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ListsCoordinator, _parse_due


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ListsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ListsCalendar(coordinator, entry)])


def _event(item: dict, due: datetime) -> CalendarEvent:
    return CalendarEvent(
        summary=item.get("title", "Item"),
        start=due,
        end=due,
        description=(
            f"Status: {item.get('status', 'open')}"
            + (f", Assigned: {item['assigned_to']}" if item.get("assigned_to") else "")
        ),
    )


class ListsCalendar(CoordinatorEntity, CalendarEntity):
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = "Lists"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming open item with a due_at."""
        now = datetime.now(timezone.utc)
        upcoming: list[tuple[datetime, dict]] = []
        for it in self.coordinator.data.get("items", []):
            due = _parse_due(it.get("due_at"))
            if due and due >= now:
                upcoming.append((due, it))
        if not upcoming:
            return None
        upcoming.sort(key=lambda p: p[0])
        due, item = upcoming[0]
        return _event(item, due)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return item events in the given date range."""
        events: list[CalendarEvent] = []
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        for it in self.coordinator.data.get("items", []):
            due = _parse_due(it.get("due_at"))
            if due and start_date <= due <= end_date:
                events.append(_event(it, due))
        return events
