"""PDP governance gate for regression promotions."""

from __future__ import annotations

import importlib
import importlib.util
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.backend.models import User
from backend.backend.pdp.audit_logger import AuditLogger
from backend.backend.pdp.schemas import PolicyRequest


def _load_policy_engine():
    spec = importlib.util.find_spec("backend.backend.pdp.policy_engine")
    if spec is None:
        return None
    module = importlib.import_module("backend.backend.pdp.policy_engine")
    return getattr(module, "PolicyEngine", None)


def write_audit(db: Session, user_id: Optional[int], action: str, resource: str, details_json: dict) -> None:
    logger = AuditLogger(db)
    logger.log_decision(
        user_id=user_id,
        action=action,
        resource_type="regression",
        resource_id=None,
        decision=details_json.get("decision", "allow"),
        metadata={"resource": resource, **details_json},
    )


def require_admin(db: Session, user_id: int, action: str, resource: str, context: dict) -> None:
    policy_engine_cls = _load_policy_engine()
    if policy_engine_cls:
        engine = policy_engine_cls(db)
        request = PolicyRequest(
            user_id=user_id,
            action=action,
            resource_type="regression",
            resource_id=None,
            context={**context, "resource": resource},
        )
        decision = engine.evaluate(request)
        allowed = decision.allowed
        details = {"decision": "allow" if allowed else "deny", "reason": decision.reason}
    else:
        user = db.query(User).filter(User.id == user_id).one_or_none()
        allowed = bool(user and (user.role or "").lower() in {"admin", "superadmin"})
        details = {"decision": "allow" if allowed else "deny", "reason": "role check"}

    write_audit(db, user_id, action, resource, {**context, **details})

    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")
