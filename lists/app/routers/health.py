"""HA-lists — Health check endpoint."""

from __future__ import annotations
import json
import os

from fastapi import APIRouter

from database import get_connection
from models import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    version = "0.0.0"
    try:
        cfg_path = os.environ.get("CONFIG_PATH", "/config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path) as f:
                version = json.load(f).get("version", version)
    except Exception:
        pass

    db_tables = 0
    try:
        conn = get_connection()
        db_tables = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
    except Exception:
        pass

    return HealthResponse(status="ok", version=version, db_tables=db_tables)
