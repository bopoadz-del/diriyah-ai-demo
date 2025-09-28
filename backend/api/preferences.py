from fastapi import APIRouter
router = APIRouter()
preferences_store = {}
@router.get("/preferences/{user_id}")
def get_preferences(user_id: str):
    return preferences_store.get(user_id, {})
@router.post("/preferences/{user_id}")
def set_preferences(user_id: str, prefs: dict):
    preferences_store[user_id] = prefs
    return {"status": "saved", "preferences": prefs}
