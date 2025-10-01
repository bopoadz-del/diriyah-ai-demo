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

### Render Debugging
- Render Shell runs `render-build.sh` to provision Python (with dev tools) and Node 18 so you can debug both backend and frontend services.
- After the build step completes you can activate the virtual environment with `source /opt/render/project/.venv/bin/activate` and run backend tasks.
- Frontend dependencies are pre-installed via `npm ci`, letting you run `npm run dev` inside the shell for UI debugging.
