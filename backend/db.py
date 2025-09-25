import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
engine = create_engine(DATABASE_URL, future=True)

def log_alert(project_id, category, message):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO alerts (project_id, category, message, created_at) VALUES (:pid,:cat,:msg, CURRENT_TIMESTAMP)"),
            {"pid": project_id, "cat": category, "msg": message}
        )
    try:
        from backend.api.alerts_ws import enqueue_alert
        import asyncio
        enqueue_alert({
            "project_id": project_id,
            "category": category,
            "message": message
        })
    except:
        pass

def log_approval(commit_sha, approver, decision):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO approvals (commit_sha, approver, decision, created_at) VALUES (:sha,:app,:dec, CURRENT_TIMESTAMP)"),
            {"sha": commit_sha, "app": approver, "dec": decision}
        )
