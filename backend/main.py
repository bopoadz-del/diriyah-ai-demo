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
    drive_error_source,
    drive_service_error,
    drive_service_ready,
    drive_stubbed,
)

app = FastAPI(title="Diriyah Brain AI", version="v1.24")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
def health_check():
    error = drive_service_error()
    return {
        "status": "ok" if error is None else "degraded",
        "version": "v1.24",
        "drive": {
            "credentials_available": drive_credentials_available(),
            "service_ready": drive_service_ready(),
            "stubbed": drive_stubbed(),
            "error": error,
            "error_source": drive_error_source(),
        },
    }
