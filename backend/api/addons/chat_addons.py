from fastapi import APIRouter, Form
from backend.services.addons.intent_classifier import classify_intent_with_explanation
from backend.services.addons.context_manager import context_manager
from backend.services.addons.entity_extractor import entity_extractor
from backend.services.addons.memory_store import memory_store
from backend.services.addons.knowledge_graph import knowledge_graph
from backend.services.addons.predictive_assistant import predictive_assistant

router = APIRouter()

@router.post("/chat_addons")
async def chat_addons(message: str = Form(...)):
    intent_result = classify_intent_with_explanation(message)
    resolved_intent = context_manager.resolve_intent(intent_result)
    entities = entity_extractor.extract(message)
    resolved_intent["entities"] = entities
    turn_id = len(context_manager.history)+1
    memory_store.add_message(message, {"id": turn_id, "intent": resolved_intent["intent"]})
    similar = memory_store.retrieve(message)
    if "component" in entities:
        knowledge_graph.add_relation("ProjectX","has_component",entities["component"])
    kg = knowledge_graph.query_relations("ProjectX")
    if len(context_manager.history)>0:
        prev = context_manager.history[-1]["intent"]["intent"]
        predictive_assistant.record_intent(prev, resolved_intent["intent"])
    suggestion = predictive_assistant.suggest_next(resolved_intent["intent"])
    context_manager.add_turn(message, resolved_intent)
    return {"intent": resolved_intent, "entities": entities, "similar_context": similar, "knowledge_graph": kg, "history": list(context_manager.history), "suggestion": suggestion, "explanation": intent_result.get("explanation")}
