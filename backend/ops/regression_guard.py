"""Regression guard hook for promotion gating."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy.orm import Session

from backend.ops.models import BackgroundJob, BackgroundJobEvent


class RegressionGuard:
    def should_promote(self, component: str, workspace_id: int, db: Session) -> Tuple[bool, str]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        has_dlq = (
            db.query(BackgroundJob)
            .filter(
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.status == "dlq",
                BackgroundJob.created_at >= cutoff,
            )
            .first()
            is not None
        )

        if has_dlq:
            allowed = False
            reason = "Promotion blocked: recent DLQ jobs detected for workspace"
        else:
            allowed = True
            reason = "Promotion allowed"

        event = BackgroundJobEvent(
            job_id=f"promotion_gate:{component}:{workspace_id}",
            event_type="promotion_gate",
            message=reason,
            data_json={
                "component": component,
                "workspace_id": workspace_id,
                "allowed": allowed,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()
        return allowed, reason
