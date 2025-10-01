import os

from fastapi import FastAPI

from backend.api import (
    alerts,
    analytics,
    debug,
    drive_diagnose,
    drive_scan,
    preferences,
    projects,
    speech,
    upload,
    users,
    vision,
)
from backend.services import google_drive

app = FastAPI(title="Diriyah Brain AI")


@app.get("/")
def root() -> dict[str, str]:
    """Return a friendly message for Render's default health probe."""

    return {
        "status": "ok",
        "message": "Diriyah Brain AI backend is running. Visit /docs for the API schema.",
    }

# Routers
app.include_router(users.router, prefix="/api")
app.include_router(drive_scan.router, prefix="/api")
app.include_router(drive_diagnose.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(debug.router, prefix="/api")
app.include_router(preferences.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(speech.router, prefix="/api")
app.include_router(vision.router, prefix="/api")

@app.get("/health")
def health():
    """Expose a lightweight health payload with Drive diagnostics."""

    credentials_available = google_drive.drive_credentials_available()
    service_error = google_drive.drive_service_error()
    return {
        "status": "ok",
        "drive": {
            "credentials_available": credentials_available,
            "service_error": service_error,
            "stubbed": (not credentials_available) or (service_error is not None),
        },
    }

@app.on_event("startup")
async def log_startup_state() -> None:
    """Emit startup diagnostics that help with Render debugging."""

    mode = "FIXTURE" if os.getenv("USE_FIXTURE_PROJECTS", "true").lower() == "true" else "GOOGLE DRIVE"
    print(f"📂 Project API running in {mode} mode")

    credentials_available = google_drive.drive_credentials_available()
    service_error = google_drive.drive_service_error()
    stubbed = (not credentials_available) or (service_error is not None)

    drive_mode = "STUBBED" if stubbed else "LIVE"
    print(
        "📁 Google Drive integration: %s (credentials_available=%s)"
        % (drive_mode, credentials_available)
    )

    if service_error:
        print(f"   ↳ Drive service error: {service_error}")

# Keep this literal for tests:
# app.include_router(users.router ...
