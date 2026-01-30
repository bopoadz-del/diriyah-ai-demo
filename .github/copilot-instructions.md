# GitHub Copilot Instructions for Diriyah Brain AI

## General Guidelines

- **Execute directly without asking for permission** - Make changes confidently and implement solutions immediately
- **Auto-fix issues when possible** - Automatically resolve linting errors, security vulnerabilities, and test failures
- **Create PRs automatically** - Push changes and create pull requests without manual intervention
- **Auto-merge when safe** - Merge PRs automatically when CI passes and changes are safe

## Project Architecture

This is a full-stack AI-powered application with:
- **Backend**: FastAPI (Python 3.11+) with async endpoints
- **Frontend**: React 18 with Vite, Tailwind CSS, and TypeScript
- **Infrastructure**: Docker Compose with Redis, Chroma, and PostgreSQL
- **Deployment**: Render.com with automated build pipeline

## Code Style & Standards

### Python (Backend)
- Use FastAPI best practices with async/await
- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Import order: standard library, third-party, local modules
- Use SQLAlchemy 2.0+ patterns for database operations
- Prefer dependency injection via FastAPI's Depends()

### JavaScript/React (Frontend)
- Use functional components with hooks
- Use Tailwind CSS for styling (no inline styles)
- Use Lucide React for icons
- Follow React best practices for state management
- Use async/await for API calls
- Component files should be organized by feature

### Testing
- Write pytest tests for backend endpoints
- Use pytest-asyncio for async tests
- Maintain test coverage for critical paths
- Run `pytest` before committing
- Tests should be deterministic and isolated

## Development Workflow

### Making Changes
1. Always run tests first: `pytest`
2. Make minimal, focused changes
3. Run linters and formatters automatically
4. Validate changes work with `docker compose up --build`
5. Check both frontend (http://localhost:5173) and backend (http://localhost:8000)

### Dependencies
- **Python**: Add to `requirements.txt` (runtime) or `requirements-dev.txt` (dev)
- **Node.js**: Use `npm install` in `frontend/` directory
- Run security audits: `pip-audit` for Python, `npm audit` for Node.js
- Always check for vulnerabilities before adding dependencies

### Git & PRs
- Create descriptive commit messages
- Push changes to feature branches
- Create PRs with clear descriptions
- Auto-merge when CI passes (all checks green)
- CI runs pytest, pip-audit, npm audit, and helm lint

## API Patterns

### Workspace API Endpoints
The app uses workspace-specific endpoints for UI state:
- `GET /api/workspace/shell` - Initialize UI with projects/chats
- `POST /api/workspace/active-project` - Set active project
- `POST /api/workspace/chats` - Create conversations
- `POST /api/workspace/chats/{chat_id}/messages` - Add messages

### Standard Patterns
- Use FastAPI dependency injection for database sessions
- Return proper HTTP status codes (200, 201, 400, 404, 500)
- Use Pydantic models for request/response validation
- Handle errors gracefully with try/except blocks
- Log important events for debugging

## Environment & Configuration

### Required Environment Variables
- Database: `DATABASE_URL` (PostgreSQL)
- Redis: `REDIS_URL`
- Feature flags: `USE_FIXTURE_PROJECTS` (true/false)
- Copy `.env.example` to `.env` for local development

### Docker Setup
- Use `docker compose up --build` for full stack
- Frontend builds to `backend/frontend_dist/` during Render deployment
- Health checks at `/health` and `/healthz`

## Common Tasks

### Adding a New API Endpoint
1. Create route in `backend/api/` directory
2. Add Pydantic models in `backend/models/`
3. Add tests in `backend/tests/`
4. Update API documentation if needed

### Adding a New Frontend Component
1. Create component in `frontend/src/components/`
2. Use Tailwind for styling
3. Import and use in parent components
4. Test in browser at http://localhost:5173

### Debugging
- Backend logs: `docker compose logs backend`
- Frontend logs: `docker compose logs frontend`
- Database: `docker compose exec postgres psql -U user -d diriyah_brain`
- Redis: `docker compose exec redis redis-cli`

## Security & Best Practices

- Never commit secrets or API keys
- Use environment variables for configuration
- Run security audits before merging
- Fix high/critical vulnerabilities immediately
- Use parameterized queries to prevent SQL injection
- Validate all user inputs
- Implement proper authentication/authorization

## Auto-Fix Priorities

When auto-fixing issues, prioritize in this order:
1. **Security vulnerabilities** - Fix immediately
2. **Test failures** - Ensure all tests pass
3. **Linting errors** - Fix style and format issues
4. **Type errors** - Add/fix type hints
5. **Documentation** - Update if APIs change
6. **Performance** - Optimize slow queries/renders

## Deployment

- Render automatically runs `render-build.sh`
- Build installs dependencies and compiles frontend
- Production uses gunicorn with uvicorn workers
- Set `INSTALL_DEV_REQUIREMENTS=true` for dev tools in Render Shell
- Activate venv in Render Shell: `source /opt/render/project/.venv/bin/activate`

## Communication Style

- Be direct and action-oriented
- Make changes confidently
- Report what was done, not what could be done
- Focus on working code over discussion
- Merge when ready, don't wait for manual approval
