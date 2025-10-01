"""User endpoints used by the admin screen and profile stub."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from backend.services import stub_state

router = APIRouter()


class UserStub(BaseModel):
    """Representation of the placeholder user served during Render debugging."""

    id: int
    name: str
    role: str
    projects: list[int]


class UpdateAck(BaseModel):
    """Stub acknowledgement returned when the UI posts user updates."""

    status: str
    message: str


class AdminUser(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str


class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    role: str | None = None


_USER_STUB = UserStub(
    id=1,
    name="Test User",
    role="Engineer",
    projects=[101, 202, 303],
)
_UPDATE_ACK = UpdateAck(status="ok", message="Updated (stub)")


@router.get("/users/me", response_model=UserStub)
def get_user() -> UserStub:
    """Return the stub response representing the authenticated user."""

    return _USER_STUB


@router.post("/users/update", response_model=UpdateAck)
def update_user() -> UpdateAck:
    """Return a stub acknowledgement for update requests."""

    return _UPDATE_ACK


@router.get("/users", response_model=List[AdminUser])
def list_users() -> List[AdminUser]:
    """Expose the in-memory users for the admin management panel."""

    return [AdminUser(**user) for user in stub_state.list_users()]


@router.post("/users", response_model=AdminUser, status_code=201)
def create_user(payload: CreateUserRequest) -> AdminUser:
    """Create a new admin user in the stub store."""

    created = stub_state.add_user(
        name=payload.name,
        email=str(payload.email),
        role=payload.role or "Project Engineer",
    )
    return AdminUser(**created)
