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

app = FastAPI(title="Diriyah Brain AI", version="v1.24")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"status": "ok", "version": "v1.24"}
