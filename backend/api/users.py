"""User-related API routes for Diriyah Brain."""

from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class UserStub(BaseModel):
    """Representation of the placeholder user served during Render debugging."""
    id: int
    name: str
    role: str
    projects: List[int]


class UpdateAck(BaseModel):
    """Stub acknowledgement returned when the UI posts user updates."""
    status: str
    message: str


_USER_STUB = UserStub(
    id=1,
    name="Test User",
    role="Engineer",
    projects=[101, 102, 103],
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
