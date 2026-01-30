import importlib
import os
from . import cad_takeoff, boq_parser, consolidated_takeoff, rag_service
from . import admin_service, analytics_service

_openai_client = None
_openai_available = True


def _get_openai_client():
    global _openai_client, _openai_available
    if _openai_client is not None or not _openai_available:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _openai_available = False
        return None
    try:
        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI", None)
        if OpenAI is None:
            _openai_available = False
            return None
        _openai_client = OpenAI(api_key=api_key)
    except Exception:
        _openai_available = False
        return None
    return _openai_client

def summarize(raw: str, query: str) -> str:
    client = _get_openai_client()
    if client is None:
        return raw
    prompt = f"""
    User asked: {query}

    Raw system output:
    {raw}

    Provide a clear, concise, professional summary in natural language.
    """
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a project delivery AI assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return resp.choices[0].message.content

def route_intent(project_id: str, query: str) -> str:
    q = query.lower()

    if "cad takeoff" in q or "quantity takeoff" in q:
        return summarize(cad_takeoff.run_takeoff(project_id, query), query)

    if "boq" in q or "bill of quantities" in q:
        return summarize(boq_parser.parse_boq(project_id, query), query)

    if "consolidated" in q:
        return summarize(consolidated_takeoff.run_consolidation(project_id, query), query)

    if "admin" in q or "user" in q or "role" in q:
        return summarize(admin_service.handle_admin_request(query), query)

    if "analytics" in q or "metrics" in q or "logs" in q:
        return summarize(analytics_service.query_logs(project_id, query), query)

    return summarize(rag_service.query_rag(project_id, query), query)
