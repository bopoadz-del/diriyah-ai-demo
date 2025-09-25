from fastapi import APIRouter, Request
from ..services.intent_router import router

# Import services so they self-register
from ..services import (
    primavera, bim, aconex, vision, cad_takeoff,
    boq_parser, consolidated_takeoff, analytics_engine,
    alerts_engine, rag_engine
)

chat = APIRouter(prefix="/api/chat", tags=["chat"])

@chat.post("""""")
async def chat_endpoint(request: Request):
    body = await request.json()
    text = body.get("message", "")
    result = router.route(text, context={})
    return {"input": text, "result": result}
