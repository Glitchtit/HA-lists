"""Lists – Todo list entities for HA.

Two entity families:
- ListsListTodo: one TodoListEntity per non-archived list, all its open + completed items
- ListsPersonTodo: one per active person, items where assigned_to matches
"""

from __future__ import annotations
import datetime as dt

import httpx
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import get_default_context

from .const import DOMAIN
from .coordinator import ListsCoordinator

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ListsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list = []

    for lst in coordinator.data.get("lists", []):
        if lst.get("archived"):
            continue
        entities.append(ListsListTodo(coordinator, entry, lst))

    for person in coordinator.data.get("persons", []):
        if not person.get("active", True):
            continue
        entities.append(ListsPersonTodo(coordinator, entry, person))

    async_add_entities(entities)


def _parse_due(value: str | None) -> dt.date | dt.datetime | None:
    """The add-on stores due_at as an ISO date ("2026-10-20") or datetime ("2026-10-20T18:00")."""
    if not value:
        return None
    if "T" not in value:
        return dt_util.parse_date(value)
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_util.get_default_time_zone())


def _due_to_api(due: dt.date | dt.datetime | None) -> str | None:
    """Inverse of _parse_due, in the add-on's local-time format."""
    if due is None:
        return None
    if isinstance(due, dt.datetime):
        return dt_util.as_local(due).strftime("%Y-%m-%dT%H:%M")
    return due.isoformat()


def _item_to_todo(item: dict) -> TodoItem:
    status = (
        TodoItemStatus.COMPLETED
        if item.get("status") == "completed"
        else TodoItemStatus.NEEDS_ACTION
    )
    return TodoItem(
        uid=str(item["id"]),
        summary=item.get("title", "Item"),
        status=status,
        due=_parse_due(item.get("due_at")),
        description=item.get("notes") or None,
    )


def _edit_payload(current: dict, item: TodoItem) -> dict:
    """Fields an HA todo edit changes on an add-on item (status is handled separately)."""
    payload: dict = {}
    if item.summary is not None and item.summary != current.get("title"):
        payload["title"] = item.summary
    notes = item.description or ""
    if notes != (current.get("notes") or ""):
        payload["notes"] = notes
    due = _due_to_api(item.due)
    if due != (current.get("due_at") or None):
        payload["due_at"] = due
    return payload


_EDIT_FEATURES = (
    TodoListEntityFeature.UPDATE_TODO_ITEM
    | TodoListEntityFeature.DELETE_TODO_ITEM
    | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
    | TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
)


class _BaseListsTodo(CoordinatorEntity, TodoListEntity):
    """Shared edit/complete/delete logic for Lists todo entities."""

    _attr_supported_features = _EDIT_FEATURES

    def _matches(self, item: dict) -> bool:
        raise NotImplementedError

    @property
    def todo_items(self) -> list[TodoItem]:
        items = []
        for it in self.coordinator.data.get("items", []):
            if self._matches(it):
                items.append(_item_to_todo(it))
        return items

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Apply an edit from HA: rename, notes, due date, and complete/reopen."""
        current = next(
            (it for it in self.coordinator.data.get("items", []) if str(it["id"]) == item.uid),
            None,
        )
        if current is None:
            raise HomeAssistantError(f"Lists item {item.uid} not found")
        base = f"{self.coordinator.addon_url}/api/items/{item.uid}"
        async with httpx.AsyncClient(verify=get_default_context(), timeout=10) as client:
            payload = _edit_payload(current, item)
            if payload:
                (await client.patch(base, json=payload)).raise_for_status()
            was_done = current.get("status") == "completed"
            now_done = item.status == TodoItemStatus.COMPLETED
            if item.status is not None and now_done != was_done:
                endpoint = "complete" if now_done else "reopen"
                (await client.post(f"{base}/{endpoint}")).raise_for_status()
        await self.coordinator.async_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items when removed from the HA todo list."""
        async with httpx.AsyncClient(verify=get_default_context(), timeout=10) as client:
            for uid in uids:
                (await client.delete(f"{self.coordinator.addon_url}/api/items/{uid}")).raise_for_status()
        await self.coordinator.async_refresh()


class ListsListTodo(_BaseListsTodo):
    """All items belonging to one list. New items from HA land in this list."""

    _attr_supported_features = _EDIT_FEATURES | TodoListEntityFeature.CREATE_TODO_ITEM

    def __init__(self, coordinator, entry, lst: dict):
        super().__init__(coordinator)
        self._list_id = lst["id"]
        self._list_name = lst["name"]
        self._attr_unique_id = f"{entry.entry_id}_list_{lst['id']}_todo"
        icon = lst.get("icon") or "📋"
        self._attr_name = f"Lists {icon} {lst['name']}"

    def _matches(self, item: dict) -> bool:
        return item.get("list_id") == self._list_id

    async def async_create_todo_item(self, item: TodoItem) -> None:
        body = {
            "list_id": self._list_id,
            "title": item.summary,
            "notes": item.description or "",
            "due_at": _due_to_api(item.due),
        }
        async with httpx.AsyncClient(verify=get_default_context(), timeout=10) as client:
            (await client.post(f"{self.coordinator.addon_url}/api/items/", json=body)).raise_for_status()
        await self.coordinator.async_refresh()


class ListsPersonTodo(_BaseListsTodo):
    """All items assigned to one person, across every list."""

    def __init__(self, coordinator, entry, person: dict):
        super().__init__(coordinator)
        self._person_id = person["entity_id"]
        name_slug = person["name"].lower().replace(" ", "_")
        self._attr_unique_id = f"{entry.entry_id}_{name_slug}_todo"
        self._attr_name = f"Lists {person['name']}"

    def _matches(self, item: dict) -> bool:
        return item.get("assigned_to") == self._person_id
