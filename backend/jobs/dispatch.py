"""Job dispatch registry."""

from __future__ import annotations

from typing import Callable, Dict

from sqlalchemy.orm import Session

from backend.ops.handlers.hydration_handler import handle_hydration


def _stub_handler(job_type: str):
    def _handler(payload: dict, headers: dict, db: Session) -> dict:
        return {"status": "completed", "job_type": job_type, "payload": payload}

    return _handler


DISPATCH_REGISTRY: Dict[str, Callable[[dict, dict, Session], dict]] = {
    "hydration": handle_hydration,
    "learning": _stub_handler("learning"),
    "evaluation": _stub_handler("evaluation"),
    "tool_run": _stub_handler("tool_run"),
}


def get_handler(job_type: str) -> Callable[[dict, dict, Session], dict]:
    if job_type not in DISPATCH_REGISTRY:
        raise ValueError(f"Unsupported job type: {job_type}")
    return DISPATCH_REGISTRY[job_type]
