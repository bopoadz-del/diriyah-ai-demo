"""Alert utilities for hydration pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.hydration.models import AlertCategory, AlertSeverity, HydrationAlert


class AlertManager:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_alert(
        self,
        workspace_id: str,
        severity: AlertSeverity,
        category: AlertCategory,
        message: str,
        run_id: int | None = None,
    ) -> HydrationAlert:
        alert = HydrationAlert(
            workspace_id=workspace_id,
            severity=severity,
            category=category,
            message=message,
            run_id=run_id,
            is_active=True,
        )
        self.db.add(alert)
        self.db.commit()
        return alert

    def acknowledge_alert(self, alert_id: int, acknowledged_by: str) -> HydrationAlert | None:
        alert = self.db.query(HydrationAlert).filter(HydrationAlert.id == alert_id).one_or_none()
        if not alert:
            return None
        alert.is_active = False
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now(timezone.utc)
        self.db.commit()
        return alert

    def close_category(self, workspace_id: str, category: AlertCategory) -> None:
        alerts = (
            self.db.query(HydrationAlert)
            .filter(
                HydrationAlert.workspace_id == workspace_id,
                HydrationAlert.category == category,
                HydrationAlert.is_active == True,
            )
            .all()
        )
        for alert in alerts:
            alert.is_active = False
            alert.acknowledged_at = datetime.now(timezone.utc)
        self.db.commit()
