"""Lists – HA custom integration setup."""

from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ADDON_URL
from .coordinator import ListsCoordinator
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "todo", "calendar"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Lists component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lists from a config entry."""
    addon_url = entry.data.get(CONF_ADDON_URL)
    coordinator = ListsCoordinator(hass, addon_url)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    # No sidebar panel of our own: the Lists add-on's ingress panel is the UI.

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Remove services only when no coordinators remain.
        from .services import _coordinators

        if not _coordinators(hass):
            async_unregister_services(hass)
    return unload_ok
