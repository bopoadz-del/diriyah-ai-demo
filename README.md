# Diriyah Brain AI v1.24
- Backend (FastAPI) with Chat/Upload/Vision/Speech/Projects/Scan-Drive/Drive-Diagnose/Preferences/Alerts
- Frontend (React) with Navbar icons, lockable Sidebar w/ refresh, Chat (mic/cam/upload), Analytics, Settings, resizable Split
- Infra: Docker Compose (backend, frontend, redis, chroma, postgres)
## Run
```bash
cp .env.example .env
docker compose up --build
```
