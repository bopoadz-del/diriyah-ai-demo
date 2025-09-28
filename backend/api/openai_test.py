import os
from fastapi import APIRouter
import openai
router = APIRouter()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
@router.get("/openai/test")
def openai_test():
    if not OPENAI_API_KEY:
        return {"status": "error", "message": "OPENAI_API_KEY not set"}
    try:
        models = openai.models.list()
        ids = [m.get("id") if isinstance(m, dict) else getattr(m, "id", None) for m in models[:3]]
        return {"status": "ok", "models_available": [i for i in ids if i]}
    except Exception as e:
        return {"status": "error", "message": str(e)}
