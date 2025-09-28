"""User-related API routes for Diriyah Brain."""

from fastapi import APIRouter

router = APIRouter()

_USER_STUB = {
    "id": 1,
    "name": "Test User",
    "role": "Engineer",
}


@router.get("/users/me")
def get_user() -> dict:
    """Return a stub response representing the authenticated user."""
    return _USER_STUB


@router.post("/users/update")
def update_user() -> dict:
    """Return a stub acknowledgement for update requests."""
    return {"status": "ok", "message": "Updated (stub)"}
