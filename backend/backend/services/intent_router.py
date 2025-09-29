import os
from openai import OpenAI
from . import cad_takeoff, boq_parser, consolidated_takeoff, rag_service
from . import admin_service, analytics_service

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize(raw: str, query: str) -> str:
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