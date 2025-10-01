"""FastAPI application entry-point for the stub backend."""

from __future__ import annotations

from fastapi import FastAPI

from backend.api import users
from backend.services import google_drive

app = FastAPI(title="Diriyah Brain Stub Backend")

app.include_router(users.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, object]:
    """Return health information for monitoring and debugging."""

    drive_details = google_drive.drive_stub_details()
    drive_payload = {**drive_details, "error": drive_details.get("detail")}

    return {"status": "ok", "drive": drive_payload}
