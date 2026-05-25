"""Standalone pytest shim for ha_lists integration helper tests.

Pre-caches stdlib modules that would be shadowed by the integration's
calendar.py, then loads services.py via importlib with mocked HA internals so
the pure helpers are testable without a live Home Assistant environment.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

# ── 1. Pre-cache stdlib modules that shadow-collide with the integration ──────
# ha_lists/calendar.py shadows stdlib calendar; import the real one first so
# httpx (imported by services.py) finds it in sys.modules before the HA file.
import calendar as _stdlib_calendar  # noqa: F401 — ensures sys.modules["calendar"] is the stdlib one
import http.cookiejar as _stdlib_cookiejar  # noqa: F401 — ditto

# ── 2. Stubs for HA modules so services.py imports without a full HA install ──
# Build minimal stubs only for the symbols services.py actually uses at
# module-load time (the HA type annotations + DOMAIN constant).
_INTEGRATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _stub(name: str, **attrs) -> types.ModuleType:
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    return m


# homeassistant.core stubs
class _SupportsResponse:
    ONLY = "only"


class _HomeAssistant:
    pass


class _ServiceCall:
    pass


_ha_core = _stub(
    "homeassistant.core",
    HomeAssistant=_HomeAssistant,
    ServiceCall=_ServiceCall,
    SupportsResponse=_SupportsResponse,
)

# homeassistant.helpers.config_validation stub
_ha_cv = _stub("homeassistant.helpers.config_validation", string=str)

# homeassistant.helpers stub
_ha_helpers = _stub("homeassistant.helpers", config_validation=_ha_cv)

# homeassistant stub tree
_ha = _stub("homeassistant")
_ha_components = _stub("homeassistant.components")
_ha_helpers_pkg = _stub("homeassistant.helpers")

for _mod_name, _mod in [
    ("homeassistant", _ha),
    ("homeassistant.core", _ha_core),
    ("homeassistant.components", _ha_components),
    ("homeassistant.helpers", _ha_helpers_pkg),
    ("homeassistant.helpers.config_validation", _ha_cv),
]:
    sys.modules.setdefault(_mod_name, _mod)

# ── 3. Load const.py so relative `from .const import DOMAIN` resolves ─────────


def _load_integration_module(bare_name: str, filename: str) -> types.ModuleType:
    path = os.path.join(_INTEGRATION_DIR, filename)
    spec = importlib.util.spec_from_file_location(f"ha_lists.{bare_name}", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "ha_lists"
    sys.modules[f"ha_lists.{bare_name}"] = mod
    spec.loader.exec_module(mod)
    return mod


# Register a minimal ha_lists package so relative imports resolve.
_ha_lists_pkg = _stub("ha_lists")
_ha_lists_pkg.__path__ = []  # empty path — prevents filesystem-based submodule lookup
_ha_lists_pkg.__package__ = "ha_lists"
sys.modules.setdefault("ha_lists", _ha_lists_pkg)

_const_mod = _load_integration_module("const", "const.py")
sys.modules["ha_lists.const"] = _const_mod

# Stub coordinator so `from .coordinator import ListsCoordinator` doesn't pull in HA.
_coordinator_stub = _stub("ha_lists.coordinator", ListsCoordinator=object)
sys.modules["ha_lists.coordinator"] = _coordinator_stub

# ── 4. Load services.py and expose as bare `services` name ────────────────────
_services_mod = _load_integration_module("services", "services.py")
sys.modules["services"] = _services_mod


import pytest  # noqa: E402


def pytest_configure(config):
    # Allow bare `@pytest.mark.asyncio` without a project-level ini.
    config.addinivalue_line("markers", "asyncio: run async test via pytest-asyncio")
