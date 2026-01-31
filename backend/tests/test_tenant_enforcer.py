import pytest
from fastapi import FastAPI
import httpx
from backend.middleware.tenant_enforcer import TenantEnforcerMiddleware

app = FastAPI()
app.add_middleware(TenantEnforcerMiddleware)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/protected")
def protected():
    return {"data": "secret"}


@pytest.mark.asyncio
async def test_health_no_tenant():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_root_no_tenant_not_403():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
        assert r.status_code != 403


@pytest.mark.asyncio
async def test_options_bypass_not_blocked_by_tenant():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.options("/api/protected")
        # FastAPI may return 405; key is middleware must NOT return 403
        assert r.status_code != 403


@pytest.mark.asyncio
async def test_protected_no_tenant_403():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/protected")
        assert r.status_code == 403
        assert "Tenant ID required" in r.text


@pytest.mark.asyncio
async def test_protected_with_tenant_not_403():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/protected", headers={"X-Tenant-ID": "test"})
        assert r.status_code != 403
