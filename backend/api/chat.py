from fastapi import APIRouter, Form
from backend.services.vector_memory import get_active_project
from backend.services.intent_router import IntentRouter
router = APIRouter()
intent_router = IntentRouter()
@router.post("/chat")
async def chat(message: str = Form(...)):
    active = get_active_project() or {}

    project_id = active.get("id") if isinstance(active, dict) else getattr(active, "id", None)
    collection = active.get("collection") if isinstance(active, dict) else getattr(active, "collection", None)
    intent_result = intent_router.route(message, project_id=project_id)
    context_docs = []
    if collection and hasattr(collection, "query"):
        try:
            res = collection.query(query_texts=[message], n_results=3)
            context_docs = res.get("documents", [[]])[0]
        except Exception:
            context_docs = []
    return {
        "intent": intent_result,
        "project_id": project_id,
        "context_docs": context_docs,
        "response": f"AI response for project {project_id or 'none'}",
    }
