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
from backend.services.google_drive import (
    drive_credentials_available,
    drive_service_error,
    drive_stubbed,
)

app = FastAPI(title="Diriyah Brain AI", version="v1.24")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def _include_router_if_available(module, tag: str) -> None:
    """Register the router exposed by ``module`` when present."""

    router = getattr(module, "router", None)
    if router is not None:
        app.include_router(router, prefix="/api", tags=[tag])


for module, tag in (
    (chat, "Chat"),
    (project, "Intel"),
    (cache, "Cache"),
    (alerts, "Alerts"),
    (drive, "Drive"),
    (openai_test, "OpenAI"),
    (upload, "Upload"),
    (vision, "Vision"),
    (speech, "Speech"),
    (projects, "Projects"),
    (preferences, "Preferences"),
    (drive_scan, "Drive"),
    (drive_diagnose, "Drive"),
    (users, "Users"),
):
    _include_router_if_available(module, tag)


@app.get("/health")
def health_check():
    error = drive_service_error()
    return {
        "status": "ok" if error is None else "degraded",
        "version": "v1.24",
        "drive": {
            "credentials_available": drive_credentials_available(),
            "stubbed": drive_stubbed(),
            "error": error,
        },
    }
