"""HA-lists — FastAPI application entry point."""

from __future__ import annotations
import json
import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database
from ha_client import get_ha_timezone

logger = logging.getLogger("lists")

VERSION = "0.0.0"
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/config.json")
try:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            VERSION = json.load(f).get("version", VERSION)
except Exception:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("DEBUG") == "1" else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Lists API v%s starting...", VERSION)

    import time as _time
    tz = os.environ.get("TZ")
    if not tz:
        try:
            options_path = os.environ.get("OPTIONS_PATH", "/data/options.json")
            if os.path.exists(options_path):
                with open(options_path) as f:
                    tz = json.load(f).get("timezone") or None
        except Exception:
            tz = None
    if not tz:
        try:
            tz = await get_ha_timezone()
        except Exception:
            tz = None
    if tz:
        os.environ["TZ"] = tz
        _time.tzset()
        logger.info("Timezone set to %s", tz)

    db_tables = database.initialize()
    logger.info("Database ready (%d tables)", db_tables)

    yield

    database.close_connection()
    logger.info("Lists API shutdown")


app = FastAPI(title="Lists", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def ingress_strip(request: Request, call_next):
    """Strip the HA ingress path prefix so routes match regardless of ingress token."""
    ingress_path = request.headers.get("X-Ingress-Path", "")
    if ingress_path and request.url.path.startswith(ingress_path):
        request.scope["path"] = request.url.path[len(ingress_path):]
    return await call_next(request)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s %s → %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


from routers import folders, health, items, lists as lists_router, subtasks, tags

app.include_router(health.router)
app.include_router(folders.router)
app.include_router(lists_router.router)
app.include_router(items.router)
app.include_router(subtasks.router)
app.include_router(tags.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")
