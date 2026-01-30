from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "change-me")
JWT_ALGORITHM = "HS256"

DEFAULT_ADMIN_USER = os.getenv("AUTH_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "secret")


@router.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    if form_data.username != DEFAULT_ADMIN_USER or form_data.password != DEFAULT_ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = jwt.encode({"sub": form_data.username, "tenant_id": 1}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/login")
async def legacy_login() -> dict:
    return {"status": "ok", "message": "Use /auth/token for OAuth2 login"}


@router.post("/auth/register")
async def register() -> dict:
    return {"status": "ok", "message": "User registration stub"}
