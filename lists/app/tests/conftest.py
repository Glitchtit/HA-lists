"""HA-lists — pytest fixtures.

`tmp_db` wipes the singleton sqlite connection and points the module at a
throwaway file so each test starts clean.
"""

from __future__ import annotations
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_lists.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    import database
    database._conn = None
    database.DB_PATH = db_path
    database.initialize()
    yield database.get_connection()
    database.close_connection()


@pytest.fixture
def client(tmp_db, monkeypatch):
    """Test client — stubs out HA person sync so startup doesn't try to
    reach the (nonexistent) Supervisor socket."""
    async def _empty_persons():
        return []
    monkeypatch.setattr("ha_client.get_persons", _empty_persons)

    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c
