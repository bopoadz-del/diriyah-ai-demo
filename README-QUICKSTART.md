# Diriyah Brain AI — Quickstart

## Prerequisites
- Docker + Docker Compose v2
- Node 20+ (if running frontend locally)
- Python 3.11+ (if running backend locally)

## 1) Environment
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

## 2) Run with Docker Compose

**Development** (hot-reload, Vite dev server):
```bash
docker compose -f docker-compose.dev.yml up --build
```
- Backend: http://localhost:8000 (with auto-reload)
- Frontend: http://localhost:5173 (Vite dev server)

**Production-like** (optimized build):
```bash
docker compose -f docker-compose.prod.yml up --build
```
- App: http://localhost:8000 (serves both API and frontend)

**Quick test** (simplified):
```bash
docker compose up --build
```
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## 3) Local Dev (no Docker)

**Backend:**
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Frontend (Vite):**
```bash
cd frontend
npm install
npm run dev
```

## 4) Model Weights
Place YOLO weights into `backend/models/` (replace the `.pt.placeholder` files).

## 5) Health Check

The backend exposes three health endpoints (all return the same payload):
- `/health` — Primary endpoint
- `/healthz` — Kubernetes-style alias
- `/api/health` — Frontend-compatible endpoint

```bash
# Quick check
curl http://localhost:8000/health

# Full check script
python3 scripts/health_check.py
```
