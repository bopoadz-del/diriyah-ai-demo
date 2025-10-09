import os
from typing import Any, Dict, List

try:  # pragma: no cover - optional dependency for Render builds
    from sqlalchemy import create_engine, text  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully
    create_engine = None  # type: ignore[assignment]
    text = None  # type: ignore[assignment]

from backend.api.alerts_ws import enqueue_alert

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
_ALERT_LOG: List[Dict[str, Any]] = []
_APPROVAL_LOG: List[Dict[str, Any]] = []

if create_engine is not None:
    engine = create_engine(DATABASE_URL, future=True)
else:  # pragma: no cover - lightweight mode
    engine = None  # type: ignore[assignment]


def log_alert(project_id, category, message):
    payload = {"project_id": project_id, "category": category, "message": message}
    if engine is not None and text is not None:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO alerts (project_id, category, message, created_at) "
                    "VALUES (:pid,:cat,:msg, CURRENT_TIMESTAMP)"
                ),
                {"pid": project_id, "cat": category, "msg": message},
            )
    else:
        _ALERT_LOG.append({**payload})
    enqueue_alert(payload)


def log_approval(commit_sha, approver, decision):
    if engine is not None and text is not None:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO approvals (commit_sha, approver, decision, created_at) "
                    "VALUES (:sha,:app,:dec, CURRENT_TIMESTAMP)"
                ),
                {"sha": commit_sha, "app": approver, "dec": decision},
            )
    else:
        _APPROVAL_LOG.append(
            {"commit_sha": commit_sha, "approver": approver, "decision": decision}
        )
