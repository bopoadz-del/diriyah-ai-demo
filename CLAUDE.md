# CLAUDE.md - AI Assistant Guide for Diriyah Brain AI

This document provides comprehensive context for AI assistants working on this codebase.

## Project Overview

**Diriyah Brain AI v1.24** is an AI-powered construction project management and intelligence platform. It provides conversational AI capabilities, document processing, analytics, and integrations with construction industry tools.

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.11), SQLAlchemy ORM |
| **Frontend** | React 18, Vite, Tailwind CSS |
| **Database** | PostgreSQL (prod), SQLite (dev) |
| **Cache/Queue** | Redis Streams |
| **Vector DB** | Chroma, FAISS |
| **Deployment** | Docker Compose (local), Render.com (prod), Kubernetes/Helm |

## Repository Structure

```
/
├── backend/                    # FastAPI application
│   ├── main.py                 # App entry point, router loading
│   ├── db.py                   # Database configuration
│   ├── api/                    # 55+ API route modules
│   ├── services/               # Business logic layer
│   ├── backend/                # Core subsystems
│   │   ├── pdp/                # Policy Decision Point (auth/access)
│   │   ├── models.py           # SQLAlchemy models
│   │   └── db.py               # Session management
│   ├── hydration/              # Data sync pipeline
│   ├── reasoning/              # Document linking (ULE)
│   ├── runtime/                # Code execution sandbox
│   ├── events/                 # Event sourcing
│   ├── jobs/                   # Background workers
│   ├── tests/                  # Test suite
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── hooks/              # Custom hooks
│   │   ├── contexts/           # React contexts
│   │   └── locales/            # i18n translations
│   ├── package.json
│   └── vite.config.js
├── deploy/                     # Kubernetes manifests
├── helm/                       # Helm chart
├── environments/               # Environment-specific configs
├── scripts/                    # Utility scripts
├── docker-compose.yml          # Local dev stack
├── render.yaml                 # Render.com deployment
└── Makefile                    # Common commands
```

## Quick Commands

```bash
# Local development
make dev                        # Start all services with docker-compose
make up                         # Start services in background
make down                       # Stop services
make test                       # Run test suite

# Without Docker
./scripts/setup-dev-env.sh      # Bootstrap venv
source .venv/bin/activate
pytest -q                       # Run tests

# Frontend only
cd frontend && npm ci && npm run dev
```

## Key Architectural Patterns

### 1. API Router Pattern
Each API module in `/backend/api/` exports a `router` object that gets dynamically loaded in `main.py`:

```python
# backend/api/chat.py
router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/")
async def send_message(...):
    ...
```

### 2. Service Layer
Business logic lives in `/backend/services/`. Services are injected via FastAPI's `Depends()`:

```python
from backend.services.intent_router import IntentRouter

@router.post("/chat")
async def chat(intent_router: IntentRouter = Depends()):
    ...
```

### 3. Policy Decision Point (PDP)
All requests pass through PDP middleware (`/backend/backend/pdp/middleware.py`) which enforces:
- Access control lists (ACL)
- Content scanning
- Rate limiting
- Audit logging

Public endpoints are exempted via `PDP_PUBLIC_PATHS` list.

### 4. Multi-Tenant Support
Requests require `X-Tenant-ID` header. Access tenant via `request.state.tenant_id`.

### 5. Fixture Mode
Set `USE_FIXTURE_PROJECTS=true` for deterministic demo data without external API dependencies.

### 6. Background Workers
Three worker processes handle async tasks:
- `hydration_worker.py` - Nightly data sync
- `queue_worker.py` - Redis Streams consumer
- `event_projector_worker.py` - Event sourcing projections

## Environment Variables

### Required for Development
```bash
DATABASE_URL=sqlite:///./app.db     # SQLite for local dev
REDIS_URL=redis://localhost:6379/0
USE_FIXTURE_PROJECTS=true           # Use fixture data
```

### Optional
```bash
OPENAI_API_KEY=                     # AI features (stubbed if empty)
GOOGLE_SERVICE_ACCOUNT=             # Google Drive (fixture if empty)
LOG_LEVEL=INFO
UNCERTAINTY_THRESHOLD=0.3
CAUSAL_CONFIDENCE_LEVEL=0.9
ENABLE_BERT_INTENT=false
```

See `.env.example` for full list.

## Testing

### Running Tests
```bash
pytest -q                           # Quick run
pytest -v                           # Verbose
pytest backend/tests/test_chat.py   # Specific file
pytest -k "test_health"             # Pattern match
```

### Test Structure
- `/backend/tests/` - Main test suite
- `/backend/tests/conftest.py` - Fixtures
- Tests organized by feature: `test_hydration/`, `test_pdp/`, `test_runtime/`, etc.

### Writing Tests
Use FastAPI TestClient with fixtures:
```python
from fastapi.testclient import TestClient
from backend.main import app

def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
```

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`):

1. **build-and-test** - Python 3.11, pip-audit, pytest
2. **frontend-audit** - npm audit (high/critical only)
3. **helm-lint-and-package** - Helm chart validation
4. **request-prod-approval** - Slack notification (main branch only)

### CI Requirements
- All dependencies must be **exact pinned** (`==`) in requirements.txt
- `pip-audit` must pass with no vulnerabilities
- `npm audit --audit-level=high` must pass

## Code Conventions

### Python
- Use type hints for function signatures
- Follow FastAPI patterns for dependency injection
- SQLAlchemy models inherit from `Base` in `backend.backend.db`
- Async preferred for I/O-bound operations

### JavaScript/React
- Functional components with hooks
- Custom hooks in `/frontend/src/hooks/`
- Tailwind CSS for styling
- i18next for internationalization

### Database
- Alembic for migrations (when needed)
- SQLite for development, PostgreSQL for production
- Models in `/backend/backend/models.py`

### API Design
- RESTful endpoints under `/api/`
- JSON responses
- Consistent error handling with HTTPException
- OpenAPI documentation auto-generated at `/docs`

## Important Files Reference

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, router loading |
| `backend/backend/pdp/middleware.py` | Auth/access middleware |
| `backend/backend/models.py` | Core database models |
| `backend/services/intent_router.py` | Chat intent classification |
| `frontend/src/App.jsx` | React root component |
| `frontend/vite.config.js` | Frontend build config |
| `docker-compose.yml` | Local dev services |
| `render.yaml` | Production deployment |
| `.github/workflows/ci.yml` | CI pipeline |

## Common Tasks

### Adding a New API Endpoint
1. Create module in `/backend/api/your_feature.py`
2. Define router: `router = APIRouter(prefix="/api/your-feature")`
3. Import in `backend/main.py` (auto-loaded if named correctly)
4. Add tests in `/backend/tests/test_your_feature.py`

### Adding a Frontend Component
1. Create component in `/frontend/src/components/`
2. Import and use in pages or other components
3. Add translations to `/frontend/src/locales/en.json` and `ar.json`

### Updating Dependencies
1. Update version in `requirements.txt` (use exact pinning: `==`)
2. Run `pip-audit` to verify no vulnerabilities
3. Test locally before committing

### Database Changes
1. Update models in `/backend/backend/models.py`
2. For SQLite dev: delete db file and restart
3. For production: create Alembic migration

## Debugging Tips

### Backend
- Set `LOG_LEVEL=DEBUG` for verbose logging
- Health check: `GET /health` and `/healthz`
- API docs: `http://localhost:8000/docs`

### Frontend
- Vite dev server: `http://localhost:5173`
- API proxy configured to backend at `:8000`
- React DevTools recommended

### Docker
```bash
docker compose logs -f backend      # Follow backend logs
docker compose exec backend bash    # Shell into container
```

## Security Notes

- Never commit `.env` files or secrets
- Use `pip-audit` before merging dependency changes
- PDP middleware enforces access control
- Content scanner blocks sensitive data patterns
- Rate limiting prevents abuse

## External Integrations

The system integrates with (configured via environment):
- **OpenAI** - GPT for chat responses
- **Google Drive** - Document storage
- **Oracle Aconex** - Document management
- **Primavera P6** - Project scheduling
- **Chroma** - Vector embeddings
- **Redis** - Caching and job queue

All integrations gracefully degrade to fixture/stub mode when credentials unavailable.
