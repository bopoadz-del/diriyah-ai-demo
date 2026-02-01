from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import jwt

router = APIRouter()
logger = logging.getLogger(__name__)

_DEV_ENVIRONMENTS = {"dev", "development", "local", "test"}


def _is_dev_environment() -> bool:
    return os.getenv("ENV", "").lower() in _DEV_ENVIRONMENTS


def _get_jwt_secret() -> str:
    """Get JWT secret, requiring it in production."""
    secret = os.getenv("JWT_SECRET_KEY")
    if secret:
        return secret
    if _is_dev_environment():
        return "insecure-dev-secret-do-not-use-in-prod"
    raise ValueError("JWT_SECRET_KEY must be set in production")


def _get_admin_credentials() -> tuple[str, str]:
    """Get admin credentials, requiring them in production."""
    user = os.getenv("AUTH_ADMIN_USER")
    password = os.getenv("AUTH_ADMIN_PASSWORD")

    if user and password:
        return user, password

    if _is_dev_environment():
        logger.warning("Using insecure dev admin credentials - do NOT use in production")
        return "dev-admin", "dev-password-insecure"

    raise ValueError(
        "AUTH_ADMIN_USER and AUTH_ADMIN_PASSWORD must be set in production. "
        "Set ENV=development for local dev without credentials."
    )


JWT_SECRET = _get_jwt_secret()
JWT_ALGORITHM = "HS256"

ADMIN_USER, ADMIN_PASSWORD = _get_admin_credentials()


@router.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    if form_data.username != ADMIN_USER or form_data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = jwt.encode({"sub": form_data.username, "tenant_id": 1}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/login")
async def legacy_login() -> dict:
    return {"status": "ok", "message": "Use /auth/token for OAuth2 login"}


@router.post("/auth/register")
async def register() -> dict:
    return {"status": "ok", "message": "User registration stub"}
