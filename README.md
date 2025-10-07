# Diriyah Brain AI v1.24

## Features
- Backend (FastAPI) with Chat, Upload, Vision, Speech, Projects, Scan-Drive, Drive-Diagnose, Preferences, Alerts, Workspace shell APIs
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
 codex/prepare-repo-for-final-render
=======
 codex/prepare-repo-for-final-render
main
  `/opt/render/project/.venv` and exposes the health check at `/health` for monitoring.
- Frontend bundles are generated during the Render build and copied into
  `backend/frontend_dist/`, so no compiled assets need to be checked into git.
- Builds install only the runtime dependencies by default; set the Render environment
  variable `INSTALL_DEV_REQUIREMENTS=true` before triggering a deploy when you need
  linting or test tools in the Render Shell for debugging.
- After opening a Render Shell, activate the environment with
  `source /opt/render/project/.venv/bin/activate` before running management or
  debugging commands.

 codex/prepare-repo-for-final-render
  `/opt/render/project/.venv` and exposes the health check at `/health` for monitoring.<<<<<<< codex/prepare-repo-for-final-render
- Frontend bundles are generated during the Render build and copied into
  `backend/frontend_dist/`, so no compiled assets need to be checked into git.

 main main

    main
### Project Mode
- Default **Fixture Mode** (no Google Drive): `USE_FIXTURE_PROJECTS=true`
- Live Google Drive Mode: set `USE_FIXTURE_PROJECTS=false` (requires Drive creds)

### Workspace API

The interactive sidebar and chat workspace consume a dedicated set of workspace endpoints
that seed the UI with deterministic project data and capture user actions for demos:

- `GET /api/workspace/shell` – hydrate the React shell with projects, chat groups, and conversations.
- `POST /api/workspace/active-project` – persist the active project selection.
- `POST /api/workspace/chats` – create a draft conversation for the selected project.
- `POST /api/workspace/chats/{chat_id}/read` – open a conversation and reset unread counts.
- `POST /api/workspace/chats/{chat_id}/messages` – append a user message to the timeline and update previews.
- `POST /api/workspace/chats/{chat_id}/attachments` – register supporting files against the context panel.
- `POST /api/workspace/microphone` – toggle the shared microphone capture state.
- `PUT /api/workspace/messages/{message_id}/action` – log quick actions taken against a message.
