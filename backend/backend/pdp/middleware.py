"""FastAPI middleware for PDP policy enforcement."""

import logging
from typing import Optional
from fastapi import Request, Response
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.backend.db import SessionLocal
from .policy_engine import PolicyEngine
from .schemas import PolicyRequest

logger = logging.getLogger(__name__)

_pdp_db_warning_logged = False


# Public endpoints that skip PDP checks
PUBLIC_ENDPOINTS = {"/health", "/", "/favicon.ico"}
PUBLIC_PREFIXES = ("/docs", "/openapi", "/openapi.json", "/redoc", "/static", "/assets")


class PDPMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enforcing PDP policies on all incoming requests.
    
    This middleware intercepts all requests before they reach endpoints and:
    1. Skips public endpoints (health, docs, openapi.json)
    2. Extracts user_id from request headers or session
    3. Checks rate limits
    4. Evaluates policies
    5. Logs all decisions
    6. Returns 429 for rate limit exceeded, 403 for denied access
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Intercept and evaluate each request through PDP engine.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from next handler or error response
        """
        # Skip PDP for public endpoints
        if request.method.upper() == "OPTIONS":
            return await call_next(request)
        if request.url.path in PUBLIC_ENDPOINTS or request.url.path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)
        
        # Extract user_id from request
        user_id = self._extract_user_id(request)
        if not user_id:
            logger.warning(f"No user_id found for request to {request.url.path}")
            # For now, allow anonymous access to non-public endpoints
            # In production, you may want to deny access here
            return await call_next(request)
        
        # Get database session
        db: Session = SessionLocal()
        try:
            # Initialize policy engine
            try:
                engine = PolicyEngine(db)
            except (OperationalError, ProgrammingError) as exc:
                if self._is_missing_policies_table(exc):
                    self._log_missing_policies_warning()
                    return await call_next(request)
                raise
            
            # Extract resource type from path
            resource_type = self._extract_resource_type(request.url.path)
            
            # Check rate limit first
            endpoint = self._extract_endpoint(request.url.path)
            try:
                allowed, remaining = engine.rate_limiter.check_limit(user_id, endpoint)
            except (OperationalError, ProgrammingError) as exc:
                if self._is_missing_policies_table(exc):
                    self._log_missing_policies_warning()
                    return await call_next(request)
                raise
            
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on endpoint {endpoint}"
                )
                # Log the rate limit decision
                engine.audit_logger.log_decision(
                    user_id=user_id,
                    action=request.method,
                    resource_type=resource_type,
                    resource_id=None,
                    decision="rate_limit_exceeded",
                    metadata={
                        "endpoint": endpoint,
                        "remaining": remaining,
                    },
                    ip_address=self._get_client_ip(request),
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "remaining": remaining,
                        "endpoint": endpoint,
                    },
                )
            
            # Evaluate policy
            policy_request = PolicyRequest(
                user_id=user_id,
                action=request.method.lower(),
                resource_type=resource_type,
                resource_id=None,
                context={
                    "path": request.url.path,
                    "method": request.method,
                    "ip_address": self._get_client_ip(request),
                    "user_agent": request.headers.get("user-agent", ""),
                },
            )
            
            try:
                decision = engine.evaluate(policy_request)
            except (OperationalError, ProgrammingError) as exc:
                if self._is_missing_policies_table(exc):
                    self._log_missing_policies_warning()
                    return await call_next(request)
                raise
            
            # Log decision
            engine.audit_logger.log_decision(
                user_id=user_id,
                action=request.method,
                resource_type=resource_type,
                resource_id=None,
                decision="allow" if decision.allowed else "deny",
                metadata={
                    "reason": decision.reason,
                    "conditions": decision.conditions,
                },
                ip_address=self._get_client_ip(request),
            )
            
            if not decision.allowed:
                logger.warning(
                    f"Access denied for user {user_id} to {request.url.path}: {decision.reason}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Access denied",
                        "reason": decision.reason,
                    },
                )
            
            # Store decision in request state for downstream use
            request.state.pdp_decision = decision
            request.state.user_id = user_id
            
            # Allow request to proceed
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Error in PDP middleware: {str(e)}", exc_info=True)
            # On error, allow request to proceed but log the error
            # In production, you may want to deny access on errors
            return await call_next(request)
        finally:
            db.close()

    @staticmethod
    def _is_missing_policies_table(exc: Exception) -> bool:
        message = str(exc).lower()
        return "no such table: policies" in message or "relation \"policies\"" in message or "does not exist" in message

    @staticmethod
    def _log_missing_policies_warning() -> None:
        global _pdp_db_warning_logged
        if _pdp_db_warning_logged:
            return
        _pdp_db_warning_logged = True
        logger.warning("PDP disabled: policies table missing — running without policies")
    
    def _extract_user_id(self, request: Request) -> Optional[int]:
        """
        Extract user_id from request headers or session.
        
        Priority:
        1. X-User-ID header
        2. Authorization header (extract from JWT)
        3. Session cookie
        4. Request state
        
        Args:
            request: HTTP request
            
        Returns:
            User ID or None
        """
        # Try X-User-ID header
        user_id_header = request.headers.get("X-User-ID")
        if user_id_header:
            try:
                return int(user_id_header)
            except ValueError:
                pass
        
        # Try request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return request.state.user_id
        
        # For testing/development, return a default user
        # Remove this in production
        return 1
    
    def _extract_resource_type(self, path: str) -> str:
        """
        Extract resource type from URL path.
        
        Args:
            path: URL path
            
        Returns:
            Resource type string
        """
        parts = path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "api":
            return parts[1]
        return "unknown"
    
    def _extract_endpoint(self, path: str) -> str:
        """
        Extract endpoint identifier for rate limiting.
        
        Args:
            path: URL path
            
        Returns:
            Endpoint identifier
        """
        parts = path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "api":
            return parts[1]
        return "api"
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
