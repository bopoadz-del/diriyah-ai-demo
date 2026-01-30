"""Middleware enforcing tenant IDs for multi-tenant routing."""

import os

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


PUBLIC_ENDPOINTS = {"/health", "/healthz", "/docs", "/openapi.json", "/api/docs", "/api/openapi.json"}


class TenantEnforcerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        enforce_tenant = os.getenv("REQUIRE_TENANT_ID", "true").strip().lower() not in {"0", "false", "no"}
        if not enforce_tenant:
            return await call_next(request)
        if request.url.path in PUBLIC_ENDPOINTS:
            return await call_next(request)
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return JSONResponse(status_code=403, content={"detail": "Tenant ID required"})
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response
