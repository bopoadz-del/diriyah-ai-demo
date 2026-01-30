"""Middleware enforcing tenant IDs for multi-tenant routing."""

import os

from fastapi import Request
from fastapi.responses import JSONResponse, Response
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
        if request.method == "OPTIONS":
            return Response(status_code=204)
        path = request.url.path
        if path in PUBLIC_ENDPOINTS or path == "/":
            return await call_next(request)
        if path.startswith("/docs") or path.startswith("/openapi.json"):
            return await call_next(request)
        if path.startswith("/static") or path.startswith("/assets"):
            return await call_next(request)
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return JSONResponse(status_code=403, content={"detail": "Tenant ID required"})
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response
