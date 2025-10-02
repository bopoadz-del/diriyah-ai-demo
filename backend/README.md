# Masterise Brain AI — Backend

FastAPI backend with Google Drive, RAG, Whisper STT, YOLO vision, and analytics.

## Run (local)
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

## Connector configuration

The following environment variables are consumed by the connector health
endpoints and the new service clients:

| Service | Required variables |
| ------- | ------------------ |
| Google Drive | `GOOGLE_SERVICE_ACCOUNT` (path to credentials) |
| Oracle Aconex | `ACONEX_BASE_URL`, `ACONEX_API_KEY`, optional `ACONEX_HEALTH_PATH`, `ACONEX_TIMEOUT` |
| Primavera P6 | `PRIMAVERA_BASE_URL`, `PRIMAVERA_USERNAME`, `PRIMAVERA_PASSWORD`, optional `PRIMAVERA_HEALTH_PATH`, `PRIMAVERA_TIMEOUT` |
| BIM/IFC service | `BIM_BASE_URL`, `BIM_AUTH_TOKEN`, optional `BIM_HEALTH_PATH`, `BIM_TIMEOUT` |
| Vision/YOLO service | `VISION_BASE_URL`, `VISION_API_KEY`, optional `VISION_HEALTH_PATH`, `VISION_TIMEOUT` |
| OneDrive | `ONEDRIVE_HEALTH_URL`, optional `ONEDRIVE_ACCESS_TOKEN`, optional `CONNECTOR_HTTP_TIMEOUT` |
| Power BI | `POWER_BI_HEALTH_URL`, optional `POWER_BI_API_KEY`, optional `CONNECTOR_HTTP_TIMEOUT` |
| Microsoft Teams | `TEAMS_HEALTH_URL` and optional `TEAMS_API_TOKEN`, or `TEAMS_WEBHOOK_URL` for webhook-only setups |

All health endpoints expect JSON responses. When the health URL returns plain
text the raw response body is exposed under the ``details.raw`` key.