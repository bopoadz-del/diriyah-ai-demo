
# Diriyah Brain AI — Quickstart

## Prereqs
- Docker + Docker Compose
- Node 20.19.0+ (if running frontend locally)
- Python 3.10+ (if running backend locally)

## 1) Environment
Copy `.env.example` to `.env` and fill in keys.

## 2) Run with Docker Compose
```bash
docker compose up -d --build
```
- Backend: http://localhost:8000 (health: `/health` and `/healthz`)
- Frontend: http://localhost:5173
> Use the root `docker-compose.yml` (the `stack/` compose file is deprecated).

Expected services after `docker compose ps`:
- backend (API)
- hydration-worker (scheduler)
- queue-worker (Redis Streams consumer)
- event-projector-worker (event projector)
- redis
- chroma
- frontend

## 3) Local Dev (no Docker)
Backend
```bash
pip install -r backend/requirements.txt
# Optional ML/NLP dependencies (torch/transformers/camel-tools, etc.)
pip install -r backend/requirements-ml.txt
uvicorn backend.main:app --reload --port 8000
```
Workers (optional local run)
```bash
python -m backend.jobs.hydration_worker
python -m backend.jobs.queue_worker
python -m backend.jobs.event_projector_worker
```
Frontend (Vite)
```bash
cd frontend
npm install
npm run dev
```

## 4) Event Flow Verification
1. Trigger a hydration/learning event (for example: POST to `/api/hydration/run-now` or `/api/learning/feedback`).
2. Check that events appear in the global stream:
```bash
curl http://localhost:8000/api/events/global?limit=10
```

## 5) Required Environment Variables
- `REDIS_URL` (example: `redis://localhost:6379/0`)
- `CHROMA_HOST` (example: `localhost` when running the chroma container)
- `CHROMA_PORT` (default: `8000`)
- `DATABASE_URL` (example: `sqlite:///./app.db` for local, or Postgres in Render)

## 6) Initialize DB explicitly
```bash
python -m backend.jobs.init_db_once
```
Notes:
- `DATABASE_URL` is preferred for Postgres or Render-managed databases.
- Use `SQLITE_PATH` for disk-backed SQLite (for example `/var/data/app.db` on Render disk).
- Without Postgres or a disk-backed SQLite volume, redeploys reset tables.

## 7) Model Weights
Place YOLO weights into `backend/models/` (replace the `.pt.placeholder` files).

## 8) Health Check
```bash
API_BASE_URL=http://localhost:8000 python3 scripts/health_check.py
```

## 9) Demo flow
1. Open http://localhost:5173.
2. Click a chat thread.
3. Send a message and confirm the assistant reply appears.
