"""Lists – Sensor entities for HA."""

from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ListsCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ListsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list = [
        ListsOverdueSensor(coordinator, entry),
        ListsOpenSensor(coordinator, entry),
    ]
    for person in coordinator.data.get("persons", []):
        if not person.get("active", True):
            continue
        entities.append(ListsPersonOpenSensor(coordinator, entry, person))
    async_add_entities(entities)


class ListsOverdueSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:alert-circle"
    _attr_native_unit_of_measurement = "items"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_overdue_count"
        self._attr_name = "Lists Overdue"

    @property
    def native_value(self):
        return self.coordinator.data.get("overdue_count", 0)


class ListsOpenSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:format-list-checks"
    _attr_native_unit_of_measurement = "items"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_open_count"
        self._attr_name = "Lists Open"

    @property
    def native_value(self):
        return self.coordinator.data.get("open_count", 0)


class ListsPersonOpenSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:account-check"
    _attr_native_unit_of_measurement = "items"

    def __init__(self, coordinator, entry, person):
        super().__init__(coordinator)
        self._person_id = person["entity_id"]
        name_slug = person["name"].lower().replace(" ", "_")
        self._attr_unique_id = f"{entry.entry_id}_{name_slug}_open"
        self._attr_name = f"Lists {person['name']} Open"

    @property
    def native_value(self):
        return sum(
            1
            for it in self.coordinator.data.get("items", [])
            if it.get("assigned_to") == self._person_id
        )
