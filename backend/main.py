import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import (
    alerts,
    cache,
    chat,
    drive,
    drive_diagnose,
    drive_scan,
    openai_test,
    preferences,
    project,
    projects,
    speech,
    upload,
    users,
    vision,
)
from backend.services import google_drive

APP_VERSION = "v1.24"

app = FastAPI(title="Diriyah Brain AI", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    """Return a friendly message for Render's default health probe."""

    return {
        "status": "ok",
        "message": "Diriyah Brain AI backend is running. Visit /docs for the API schema.",
        "version": APP_VERSION,
    }


# Routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(project.router, prefix="/api", tags=["Intel"])
app.include_router(cache.router, prefix="/api", tags=["Cache"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(drive.router, prefix="/api", tags=["Drive"])
app.include_router(openai_test.router, prefix="/api", tags=["OpenAI"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(vision.router, prefix="/api", tags=["Vision"])
app.include_router(speech.router, prefix="/api", tags=["Speech"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(preferences.router, prefix="/api", tags=["Preferences"])
app.include_router(drive_scan.router, prefix="/api", tags=["Drive"])
app.include_router(drive_diagnose.router, prefix="/api", tags=["Drive"])
app.include_router(users.router, prefix="/api", tags=["Users"])


@app.get("/health")
def health() -> dict[str, object]:
    """Expose a lightweight health payload with Drive diagnostics."""

    credentials_available = google_drive.drive_credentials_available()
    service_error = google_drive.drive_service_error()
    return {
        "status": "ok",
        "version": APP_VERSION,
        "drive": {
            "credentials_available": credentials_available,
            "service_error": service_error,
            "stubbed": (not credentials_available) or (service_error is not None),
        },
    }


@app.on_event("startup")
async def log_startup_state() -> None:
    """Emit startup diagnostics that help with Render debugging."""

    print(f"🚀 Diriyah Brain AI {APP_VERSION} starting up")
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
