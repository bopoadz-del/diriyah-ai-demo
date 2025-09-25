from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant = request.headers.get('X-Tenant', 'default')
        request.state.tenant = tenant
        response = await call_next(request)
        response.headers['X-Tenant'] = tenant
        return response
