import os
from fastapi import FastAPI
from backend.api import users, projects, alerts, drive_scan, drive_diagnose, preferences

app = FastAPI(title="Diriyah Brain AI")

# Routers
app.include_router(users.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(drive_scan.router, prefix="/api")
app.include_router(drive_diagnose.router, prefix="/api")
app.include_router(preferences.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def log_project_mode():
    mode = "FIXTURE" if os.getenv("USE_FIXTURE_PROJECTS", "true").lower() == "true" else "GOOGLE DRIVE"
    print(f"📂 Project API running in {mode} mode")

# Keep this literal for tests:
# app.include_router(users.router ...
