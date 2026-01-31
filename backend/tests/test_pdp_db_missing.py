import importlib

import pytest
from fastapi import FastAPI
import httpx


@pytest.mark.asyncio
async def test_pdp_missing_policies_table_fails_open(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    import backend.backend.db as db_module
    importlib.reload(db_module)

    import backend.backend.pdp.middleware as pdp_middleware
    importlib.reload(pdp_middleware)

    app = FastAPI()
    app.add_middleware(pdp_middleware.PDPMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/protected")
    def protected():
        return {"data": "ok"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health_response = await client.get("/health")
        assert health_response.status_code == 200

        response = await client.get("/api/protected")
        assert response.status_code != 500
