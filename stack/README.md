# One-command local stack

1. Copy `.env.example` → `.env` and set secrets.
2. Place `service_account.json` next to this folder (repo root).
3. Run:
   docker compose -f stack/docker-compose.yml up --build

- Frontend on http://localhost:5173 (Nginx serving built React; proxies /api to backend)
- Backend  on http://localhost:8000