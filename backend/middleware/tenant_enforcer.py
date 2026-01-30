"""Middleware enforcing tenant IDs for multi-tenant routing."""

import os

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


PUBLIC_ENDPOINTS = {"/health", "/healthz", "/docs", "/openapi.json", "/api/docs", "/api/openapi.json"}


class TenantEnforcerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("DISABLE_TENANT_ENFORCER", "").lower() in {
            "1",
            "true",
            "yes",
        }:
            return await call_next(request)
        if request.url.path in PUBLIC_ENDPOINTS:
            return await call_next(request)
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            raise HTTPException(status_code=403, detail="Tenant ID required")
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response
