from fastapi import Request
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class TenantEnforcerMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        path = request.url.path
        method = request.method.upper()

        # Bypass CORS preflight
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Bypass health + landing + docs + static
        bypass_exact = {"/", "/favicon.ico", "/health", "/healthz"}
        bypass_prefixes = ("/assets", "/docs", "/openapi", "/openapi.json", "/redoc", "/static")

        if path in bypass_exact or path.startswith(bypass_prefixes):
            await self.app(scope, receive, send)
            return

        tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("X-Workspace-ID")
        if not tenant_id:
            resp = JSONResponse(status_code=403, content={"detail": "Tenant ID required"})
            await resp(scope, receive, send)
            return

        scope["tenant_id"] = tenant_id
        await self.app(scope, receive, send)
