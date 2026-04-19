"""Lists – HA custom integration setup."""

from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ADDON_URL, PANEL_TITLE, PANEL_ICON, PANEL_URL
from .coordinator import ListsCoordinator

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

    if not hass.data[DOMAIN].get("panel_registered"):
        try:
            hass.components.frontend.async_register_built_in_panel(
                "iframe",
                PANEL_TITLE,
                PANEL_ICON,
                PANEL_URL,
                {"url": addon_url},
                require_admin=False,
            )
            hass.data[DOMAIN]["panel_registered"] = True
        except Exception as exc:
            _LOGGER.warning("Could not register panel: %s", exc)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
