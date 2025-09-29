
# Masterise Brain AI — Quickstart

## Prereqs
- Docker + Docker Compose
- Node 18+ (if running frontend locally)
- Python 3.10+ (if running backend locally)

## 1) Environment
Copy `.env.example` to `.env` and fill in keys.

## 2) Run with Docker Compose
```bash
docker compose up --build
```
- Backend: http://localhost:8000 (health: `/healthz`)
- Frontend: http://localhost:5173

## 3) Local Dev (no Docker)
Backend
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```
Frontend (Vite)
```bash
cd frontend
npm install
npm run dev
```

## 4) Model Weights
Place YOLO weights into `backend/models/` (replace the `.pt.placeholder` files).

## 5) Health Check
```bash
API_BASE_URL=http://localhost:8000 python3 scripts/health_check.py
```
