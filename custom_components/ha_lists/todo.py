"""Lists – Todo list entities for HA.

Two entity families:
- ListsListTodo: one TodoListEntity per non-archived list, all its open + completed items
- ListsPersonTodo: one per active person, items where assigned_to matches
"""

from __future__ import annotations
import logging

import httpx
from homeassistant.components.todo import TodoListEntity, TodoItem, TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ListsCoordinator

_LOGGER = logging.getLogger(__name__)


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
        due=item.get("due_at"),
        description=item.get("notes") or None,
    )


class _BaseListsTodo(CoordinatorEntity, TodoListEntity):
    """Shared completion/delete logic for Lists todo entities."""

    def _matches(self, item: dict) -> bool:
        raise NotImplementedError

    @property
    def todo_items(self) -> list[TodoItem]:
        items = []
        for it in self.coordinator.data.get("items", []):
            if self._matches(it):
                items.append(_item_to_todo(it))
        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Not supported – items are created via the add-on UI."""
        pass

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Mark an item complete/reopen when toggled in HA."""
        endpoint = "complete" if item.status == TodoItemStatus.COMPLETED else "reopen"
        url = f"{self.coordinator.addon_url}/api/items/{item.uid}/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url)
            await self.coordinator.async_request_refresh()
        except Exception as exc:
            _LOGGER.warning("Lists todo update failed: %s", exc)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items when removed from the HA todo list."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                for uid in uids:
                    await client.delete(f"{self.coordinator.addon_url}/api/items/{uid}")
            await self.coordinator.async_request_refresh()
        except Exception as exc:
            _LOGGER.warning("Lists todo delete failed: %s", exc)


class ListsListTodo(_BaseListsTodo):
    """All items belonging to one list."""

    def __init__(self, coordinator, entry, lst: dict):
        super().__init__(coordinator)
        self._list_id = lst["id"]
        self._list_name = lst["name"]
        self._attr_unique_id = f"{entry.entry_id}_list_{lst['id']}_todo"
        icon = lst.get("icon") or "📋"
        self._attr_name = f"Lists {icon} {lst['name']}"

    def _matches(self, item: dict) -> bool:
        return item.get("list_id") == self._list_id


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
