# Masterise Brain AI — Monorepo (Render-friendly)

This repo contains:
- `backend/` — FastAPI (Gunicorn + Uvicorn workers), Google Drive, RAG, Whisper, YOLO.
- `frontend/` — React built with Vite, served via Nginx (proxies `/api` to backend).
- `stack/` — `docker-compose.yml` for local dev mirroring Render prod.

## Local (Docker)
1. Copy `stack/.env.example` to `stack/.env` and set secrets.
2. Place your Google `service_account.json` at repo root (same level as `stack/`).
3. Run:
   ```bash
   docker compose -f stack/docker-compose.yml up --build
   ```
4. Open:
   - Frontend: http://localhost:5173
   - Backend:  http://localhost:8000/health

## Deploy on Render
- Create two Render Web Services from this repo:
  - **backend** → path `backend/` (Dockerfile included). Set env vars in dashboard.
  - **frontend** → path `frontend/` (Dockerfile + nginx.conf). Edit `nginx.conf` proxy_pass to your backend URL.
- Push to GitHub, connect services, deploy.

## Notes
- Pinned dependencies for stability:
  - See `backend/backend/requirements.txt` and `frontend/package.json`.
- Uploads & indexes persist in bind-mounts under `backend/uploads`, `backend/images`, `backend/storage` in Docker Compose.