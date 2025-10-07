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

Optional Drive-backed demo data can be supplied via the following variables:

* `ANALYTICS_DRIVE_FILE_ID`, `ANALYTICS_ACTIVITY_FILE_ID`, `ANALYTICS_RULES_FILE_ID`, `ANALYTICS_TEXT_FILE_ID`
* `PRIMAVERA_DRIVE_FILE_ID`
* `ACONEX_DRIVE_FILE_ID`

When these values are omitted the backend falls back to deterministic stub data.

All health endpoints expect JSON responses. When the health URL returns plain
text the raw response body is exposed under the ``details.raw`` key.

## Feature availability overview

The demo exercises a mixture of fully mocked and environment-aware services so
Render deployments stay deterministic while still surfacing integration points.

| Capability | Backend status | Notes |
| --- | --- | --- |
| Document parsing | Drive-backed with resilient fallbacks. | ``/parsing/extract`` downloads files from Google Drive via ``download_file`` before running ``extract_file_content``; the helper falls back to stub text when Drive credentials are unavailable. |
| Invoice parsing | Placeholder | ``parse_invoice`` currently returns a stub payload and should be replaced with the production extractor when available. |
| Quantity take-off (QTO) | Demo-ready with stubbed Drive downloads when Google APIs are unavailable. | ``generate_qto`` parses DWG/IFC files after calling ``download_file``; the new Drive wrapper writes a temporary stub if the managed service cannot be reached so the pipeline can still respond. |
| Analytics engine | Drive-aware summary with stubs | ``/analytics`` and ``/analytics/summary`` accept Drive file identifiers (or environment defaults) to hydrate activity streams, rules, and compliance text while retaining canned fallbacks. |
| AutoCAD / CAD take-off | Drive-backed stub | ``CADTakeoffService.process_dwg`` now downloads the DWG from Drive and attempts to parse it; on stub data it returns deterministic geometry metadata so UI flows stay functional. |
| Primavera P6 connector | Environment-aware integration with Drive stub | ``PrimaveraClient`` performs live health checks when credentials are configured and now returns Drive-backed schedule data with ``status='stubbed'`` when configuration is missing. |
| Oracle Aconex connector | Environment-aware integration with Drive stub | ``AconexClient`` mirrors the Primavera flow, surfacing Drive-seeded transmittals when credentials are absent. |

