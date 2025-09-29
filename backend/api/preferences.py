"""Simple in-memory preferences API used for Render debugging."""

from typing import Any, Dict

from fastapi import APIRouter, Body


router = APIRouter()


# We intentionally keep the store in memory for the debugging environment.
_preferences_store: Dict[str, Dict[str, Any]] = {}


@router.get("/preferences/{user_id}")
def get_preferences(user_id: str) -> Dict[str, Any]:
    """Return the stored preferences for ``user_id`` (if any)."""

    return dict(_preferences_store.get(user_id, {}))


@router.post("/preferences/{user_id}")
def set_preferences(
    user_id: str,
    prefs: Dict[str, Any] = Body(default_factory=dict),
) -> Dict[str, Any]:
    """Persist the submitted preferences for ``user_id`` in memory."""

    _preferences_store[user_id] = dict(prefs)
    return {"status": "saved", "preferences": dict(_preferences_store[user_id])}
