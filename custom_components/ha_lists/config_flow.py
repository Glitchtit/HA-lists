"""Lists – Config flow for HA integration."""

from __future__ import annotations
import logging
import os
import voluptuous as vol
import httpx
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_ADDON_URL, DEFAULT_ADDON_URL, ADDON_SLUG

_LOGGER = logging.getLogger(__name__)


async def _discover_addon_url() -> str | None:
    """Try to auto-discover the add-on URL via Supervisor API."""
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"http://supervisor/addons/{ADDON_SLUG}/info",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                hostname = data.get("hostname") or data.get("ip_address")
                if hostname:
                    return f"http://{hostname}:8099"
    except Exception as e:
        _LOGGER.debug("Supervisor add-on discovery failed: %s", e)
    return None


async def _test_connection(url: str) -> bool:
    """Return True if the add-on health endpoint responds OK."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{url.rstrip('/')}/api/health")
            return resp.status_code == 200
    except Exception:
        return False


class ListsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lists."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        discovered_url = await _discover_addon_url()

        if user_input is not None:
            addon_url = user_input[CONF_ADDON_URL].rstrip("/")
            if not await _test_connection(addon_url):
                errors[CONF_ADDON_URL] = "cannot_connect"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured(
                    updates={CONF_ADDON_URL: addon_url}
                )
                return self.async_create_entry(
                    title="Lists",
                    data={CONF_ADDON_URL: addon_url},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_ADDON_URL,
                    default=discovered_url or DEFAULT_ADDON_URL,
                ): str,
            }),
            errors=errors,
        )
