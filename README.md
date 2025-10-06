# Diriyah Brain AI v1.24

## Features
- Backend (FastAPI) with Chat, Upload, Vision, Speech, Projects, Scan-Drive, Drive-Diagnose, Preferences, Alerts
- Frontend (React) with:
  - Navbar with Lucide icons
  - Lockable Sidebar (with Refresh)
  - Chat with Mic, Camera, File upload
  - Analytics (bar chart)
  - Settings (user preferences)
  - Resizable Split View (Chat + Analytics)
- Infra: Docker Compose (backend, frontend, redis, chroma, postgres)

## Run
```bash
cp .env.example .env
docker compose up --build
```

## Deploy to Render.com
- Render automatically runs `render-build.sh` to install system dependencies, build the
  frontend, and prepare the FastAPI app for production.
- The backend service defined in `render.yaml` uses the generated virtual environment at
  `/opt/render/project/.venv` and exposes the health check at `/health` for monitoring.<<<<<<< codex/prepare-repo-for-final-render
- Frontend bundles are generated during the Render build and copied into
  `backend/frontend_dist/`, so no compiled assets need to be checked into git.

 main

### Project Mode
- Default **Fixture Mode** (no Google Drive): `USE_FIXTURE_PROJECTS=true`
- Live Google Drive Mode: set `USE_FIXTURE_PROJECTS=false` (requires Drive creds)
