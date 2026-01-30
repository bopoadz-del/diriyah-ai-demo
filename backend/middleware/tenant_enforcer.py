"""Middleware enforcing tenant IDs for multi-tenant routing."""

from fastapi import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


PUBLIC_ENDPOINTS = {"/", "/health", "/healthz"}
PUBLIC_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/api/docs",
    "/api/openapi.json",
    "/static",
    "/assets",
    "/favicon.ico",
)


class TenantEnforcerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in PUBLIC_ENDPOINTS or request.url.path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return JSONResponse(status_code=403, content={"detail": "Tenant ID required"})
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response
