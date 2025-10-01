"""FastAPI application entry-point for the stub backend."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api import users
from backend.services import google_drive

logger = logging.getLogger(__name__)

app = FastAPI(title="Diriyah Brain Stub Backend")

app.include_router(users.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, object]:
    """Return health information for monitoring and debugging."""

    drive_details = google_drive.drive_stub_details()
    drive_payload = {**drive_details, "error": drive_details.get("detail")}

    return {"status": "ok", "drive": drive_payload}


FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend_dist"

if FRONTEND_DIST.exists():
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        logger.warning("Frontend dist detected at '%s' but index.html is missing", FRONTEND_DIST)
    else:
        logger.info("Serving compiled frontend from '%s'", FRONTEND_DIST)
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    logger.warning("Frontend build directory '%s' not found. Root requests will return the API JSON 404.", FRONTEND_DIST)
