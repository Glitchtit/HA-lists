"""Due times are local (Home Assistant's time zone), and date-only items are whole days.

The add-on stores due_at as naive local time ("2026-11-17T18:00") or a date
("2026-11-17"). The overdue count and the calendar used to read both as UTC.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
import sys
import types
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import pytest

_INTEGRATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HELSINKI = ZoneInfo("Europe/Helsinki")


def _stub(name: str, **attrs) -> types.ModuleType:
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    return m


# The parts of homeassistant.util.dt the integration uses, with the time zone fixed to Helsinki.
def _now() -> dt.datetime:
    return dt.datetime.now(HELSINKI)


_dt_util = _stub(
    "homeassistant.util.dt",
    get_default_time_zone=lambda: HELSINKI,
    parse_date=lambda s: dt.date.fromisoformat(s),
    parse_datetime=lambda s: dt.datetime.fromisoformat(s),
    now=lambda: _now(),
    start_of_local_day=lambda d: dt.datetime.combine(d, dt.time(), tzinfo=HELSINKI),
)


@dataclass
class _CalendarEvent:
    summary: str
    start: dt.date | dt.datetime
    end: dt.date | dt.datetime
    description: str | None = None


class _CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


for _name, _mod in [
    ("homeassistant.util.dt", _dt_util),
    ("homeassistant.helpers.update_coordinator", _stub(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=object,
        UpdateFailed=Exception,
        CoordinatorEntity=_CoordinatorEntity,
    )),
    ("homeassistant.helpers.entity_platform", _stub(
        "homeassistant.helpers.entity_platform", AddEntitiesCallback=object,
    )),
    ("homeassistant.components.calendar", _stub(
        "homeassistant.components.calendar",
        CalendarEntity=object,
        CalendarEvent=_CalendarEvent,
    )),
]:
    sys.modules.setdefault(_name, _mod)
sys.modules["homeassistant.util"].dt = sys.modules["homeassistant.util.dt"]

# A package of its own, so the real coordinator does not replace conftest's stub for other tests.
_pkg = _stub("ha_lists_due")
_pkg.__path__ = []
sys.modules["ha_lists_due"] = _pkg


def _load(bare: str):
    spec = importlib.util.spec_from_file_location(
        f"ha_lists_due.{bare}", os.path.join(_INTEGRATION_DIR, f"{bare}.py")
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "ha_lists_due"
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_load("const")
coordinator = _load("coordinator")
calendar = _load("calendar")

NOW = dt.datetime(2026, 11, 17, 12, 0, tzinfo=HELSINKI)


def test_naive_due_time_is_helsinki_local():
    due = coordinator._parse_due("2026-11-17T18:00")
    assert due == dt.datetime(2026, 11, 17, 16, 0, tzinfo=dt.timezone.utc)


def test_explicit_offset_is_kept():
    due = coordinator._parse_due("2026-11-17T18:00Z")
    assert due == dt.datetime(2026, 11, 17, 18, 0, tzinfo=dt.timezone.utc)


def test_timed_item_is_overdue_once_its_local_time_passes():
    at = lambda h, m: dt.datetime(2026, 11, 17, h, m, tzinfo=HELSINKI)  # noqa: E731
    due = coordinator._parse_due("2026-11-17T18:00")
    assert not coordinator._is_overdue(due, at(17, 59))
    assert coordinator._is_overdue(due, at(18, 1))


def test_date_only_due_today_is_not_overdue_yesterday_is():
    assert not coordinator._is_overdue(coordinator._parse_due("2026-11-17"), NOW)
    assert coordinator._is_overdue(coordinator._parse_due("2026-11-16"), NOW)
    assert not coordinator._is_overdue(None, NOW)


def _calendar(items):
    cal = calendar.ListsCalendar.__new__(calendar.ListsCalendar)
    cal.coordinator = types.SimpleNamespace(data={"items": items})
    return cal


@pytest.mark.asyncio
async def test_date_only_item_is_an_all_day_event():
    cal = _calendar([{"title": "Bins", "due_at": "2026-11-17"}])
    start = dt.datetime(2026, 11, 16, tzinfo=HELSINKI)
    events = await cal.async_get_events(None, start, start + dt.timedelta(days=7))
    assert [(e.start, e.end) for e in events] == [(dt.date(2026, 11, 17), dt.date(2026, 11, 18))]
    # A range that ends where the day starts does not include it.
    assert await cal.async_get_events(None, start, dt.datetime(2026, 11, 17, tzinfo=HELSINKI)) == []


@pytest.mark.asyncio
async def test_timed_item_event_is_at_local_time():
    cal = _calendar([{"title": "Call", "due_at": "2026-11-17T18:00"}])
    start = dt.datetime(2026, 11, 17, tzinfo=HELSINKI)
    events = await cal.async_get_events(None, start, start + dt.timedelta(days=1))
    assert [e.start for e in events] == [dt.datetime(2026, 11, 17, 18, 0, tzinfo=HELSINKI)]


def test_current_event_includes_todays_all_day_item(monkeypatch):
    monkeypatch.setattr(sys.modules["homeassistant.util.dt"], "now", lambda: NOW)
    cal = _calendar([
        {"title": "Old", "due_at": "2026-11-16"},
        {"title": "Later", "due_at": "2026-11-17T18:00"},
        {"title": "Today", "due_at": "2026-11-17"},
    ])
    assert cal.event.summary == "Today"
