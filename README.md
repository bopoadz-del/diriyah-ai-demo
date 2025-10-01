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

### Project Mode
- Default **Fixture Mode** (no Google Drive): `USE_FIXTURE_PROJECTS=true`
- Live Google Drive Mode: set `USE_FIXTURE_PROJECTS=false` (requires Drive creds)

## Render deployment & debugging

- **Build hook**: When using Render's native build environment, configure the
  service to run `render-build.sh` so that system packages and Python
  dependencies are installed inside a virtual environment optimised for remote
  debugging.
- **Start command**: The service runs `uvicorn backend.main:app` on port 8000;
  logs printed during startup include Google Drive integration diagnostics to
  confirm whether credentials are available.
- **Debug endpoint**: `GET /api/debug/render` returns a JSON payload with Render
  metadata (region, commit, host) and redacted connection details for PostgreSQL,
  Redis, and the OpenAI API key to simplify environment validation.
