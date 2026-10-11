"""Setting up the integration registers no sidebar panel of its own.

The Lists add-on's ingress panel is the UI. The integration's old iframe
panel pointed at the add-on's internal address, which a browser cannot reach,
and the call it used no longer exists in Home Assistant 2026.10.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from types import SimpleNamespace

import pytest

_INTEGRATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# conftest.py registers the "ha_lists" package (const, a stub coordinator and
# services); load __init__.py as a plain module beside them, so its relative
# imports resolve to those instead of the real HA-bound modules.
_spec = importlib.util.spec_from_file_location(
    "ha_lists._setup_under_test",
    os.path.join(_INTEGRATION_DIR, "__init__.py"),
    submodule_search_locations=None,
)
integration = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = integration
_spec.loader.exec_module(integration)


class _Coordinator:
    def __init__(self, hass, addon_url):
        self.addon_url = addon_url

    async def async_config_entry_first_refresh(self):
        return None


@pytest.mark.asyncio
async def test_setup_registers_no_panel_and_logs_no_panel_warning(monkeypatch, caplog):
    monkeypatch.setattr(integration, "ListsCoordinator", _Coordinator)
    monkeypatch.setattr(integration, "async_register_services", lambda hass: None)

    async def _forward(entry, platforms):
        return None

    hass = SimpleNamespace(data={}, config_entries=SimpleNamespace(async_forward_entry_setups=_forward))
    await integration.async_setup(hass, {})
    entry = SimpleNamespace(data={"addon_url": "http://0a9ed235-ha-lists:8099"}, entry_id="e1")
    with caplog.at_level(logging.WARNING):
        assert await integration.async_setup_entry(hass, entry) is True
    assert "panel" not in caplog.text.lower()
    assert list(hass.data[integration.DOMAIN]) == ["e1"]
