"""Alert Manager - Alert when metrics fall below thresholds."""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from .models import EvaluationAlert, TestRun as TestRunModel
from .schemas import Alert, AlertType, AlertSeverity
from .test_harness import THRESHOLDS

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage evaluation alerts when metrics fall below thresholds."""

    def check_thresholds(
        self,
        test_run_id: int,
        db: Session
    ) -> List[Alert]:
        """Check if test run metrics breach thresholds and create alerts.

        Args:
            test_run_id: ID of the test run to check
            db: Database session

        Returns:
            List of generated alerts
        """
        test_run = db.query(TestRunModel).filter(
            TestRunModel.id == test_run_id
        ).first()

        if not test_run:
            return []

        alerts = []
        suite = test_run.test_suite
        accuracy = test_run.accuracy_score or 0
        threshold = THRESHOLDS.get(suite, 0.90)

        # Check accuracy threshold
        if accuracy < threshold:
            severity = AlertSeverity.CRITICAL if accuracy < threshold * 0.9 else AlertSeverity.WARNING
            alert = self._create_alert(
                alert_type=AlertType.THRESHOLD_BREACH,
                severity=severity,
                message=f"{suite} accuracy ({accuracy:.1%}) below threshold ({threshold:.1%})",
                metric_name=f"{suite}_accuracy",
                current_value=accuracy,
                threshold_value=threshold,
                test_run_id=test_run_id,
                db=db
            )
            alerts.append(alert)

        # Check for significant accuracy drop from previous run
        previous_run = db.query(TestRunModel).filter(
            TestRunModel.test_suite == suite,
            TestRunModel.id < test_run_id,
            TestRunModel.status == "completed"
        ).order_by(TestRunModel.id.desc()).first()

        if previous_run and previous_run.accuracy_score:
            drop = previous_run.accuracy_score - accuracy
            if drop > 0.05:  # More than 5% drop
                alert = self._create_alert(
                    alert_type=AlertType.ACCURACY_DROP,
                    severity=AlertSeverity.WARNING,
                    message=f"{suite} accuracy dropped by {drop:.1%} from previous run",
                    metric_name=f"{suite}_accuracy_change",
                    current_value=accuracy,
                    threshold_value=previous_run.accuracy_score,
                    test_run_id=test_run_id,
                    db=db
                )
                alerts.append(alert)

        # Check for repeated failures
        recent_runs = db.query(TestRunModel).filter(
            TestRunModel.test_suite == suite,
            TestRunModel.status == "completed"
        ).order_by(TestRunModel.id.desc()).limit(3).all()

        if len(recent_runs) >= 3:
            all_below = all(
                (r.accuracy_score or 0) < threshold
                for r in recent_runs
            )
            if all_below:
                alert = self._create_alert(
                    alert_type=AlertType.TEST_FAILURE,
                    severity=AlertSeverity.CRITICAL,
                    message=f"{suite} has failed threshold 3 consecutive times",
                    metric_name=f"{suite}_consecutive_failures",
                    test_run_id=test_run_id,
                    db=db
                )
                alerts.append(alert)

        return alerts

    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        db: Session,
        metric_name: Optional[str] = None,
        current_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
        test_run_id: Optional[int] = None
    ) -> Alert:
        """Create and store an alert.

        Args:
            alert_type: Type of alert
            severity: Alert severity
            message: Alert message
            db: Database session
            metric_name: Name of affected metric
            current_value: Current metric value
            threshold_value: Threshold that was breached
            test_run_id: Associated test run ID

        Returns:
            Created Alert
        """
        alert_model = EvaluationAlert(
            alert_type=alert_type.value,
            severity=severity.value,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            test_run_id=test_run_id
        )

        db.add(alert_model)
        db.commit()
        db.refresh(alert_model)

        logger.warning(f"Alert created: [{severity.value}] {message}")

        return Alert(
            id=alert_model.id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            test_run_id=test_run_id,
            acknowledged=alert_model.acknowledged,
            acknowledged_by=alert_model.acknowledged_by,
            acknowledged_at=alert_model.acknowledged_at,
            created_at=alert_model.created_at
        )

    def get_active_alerts(
        self,
        db: Session,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50
    ) -> List[Alert]:
        """Get active (unacknowledged) alerts.

        Args:
            db: Database session
            severity: Filter by severity
            limit: Maximum number of alerts to return

        Returns:
            List of active alerts
        """
        query = db.query(EvaluationAlert).filter(
            EvaluationAlert.acknowledged == False
        )

        if severity:
            query = query.filter(EvaluationAlert.severity == severity.value)

        query = query.order_by(EvaluationAlert.created_at.desc()).limit(limit)

        results = query.all()

        return [
            Alert(
                id=r.id,
                alert_type=AlertType(r.alert_type),
                severity=AlertSeverity(r.severity),
                message=r.message,
                metric_name=r.metric_name,
                current_value=r.current_value,
                threshold_value=r.threshold_value,
                test_run_id=r.test_run_id,
                acknowledged=r.acknowledged,
                acknowledged_by=r.acknowledged_by,
                acknowledged_at=r.acknowledged_at,
                created_at=r.created_at
            )
            for r in results
        ]

    def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by: int,
        db: Session
    ) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User ID who acknowledged
            db: Database session

        Returns:
            True if acknowledgment succeeded
        """
        alert = db.query(EvaluationAlert).filter(
            EvaluationAlert.id == alert_id
        ).first()

        if not alert:
            logger.warning(f"Alert {alert_id} not found")
            return False

        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()

        db.commit()
        logger.info(f"Alert {alert_id} acknowledged by user {acknowledged_by}")

        return True

    def get_alert_history(
        self,
        db: Session,
        days: int = 30,
        limit: int = 100
    ) -> List[Alert]:
        """Get alert history.

        Args:
            db: Database session
            days: Number of days of history
            limit: Maximum number of alerts

        Returns:
            List of historical alerts
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        results = db.query(EvaluationAlert).filter(
            EvaluationAlert.created_at >= cutoff
        ).order_by(
            EvaluationAlert.created_at.desc()
        ).limit(limit).all()

        return [
            Alert(
                id=r.id,
                alert_type=AlertType(r.alert_type),
                severity=AlertSeverity(r.severity),
                message=r.message,
                metric_name=r.metric_name,
                current_value=r.current_value,
                threshold_value=r.threshold_value,
                test_run_id=r.test_run_id,
                acknowledged=r.acknowledged,
                acknowledged_by=r.acknowledged_by,
                acknowledged_at=r.acknowledged_at,
                created_at=r.created_at
            )
            for r in results
        ]

    def clear_old_alerts(
        self,
        db: Session,
        days: int = 90
    ) -> int:
        """Clear old acknowledged alerts.

        Args:
            db: Database session
            days: Delete alerts older than this many days

        Returns:
            Number of alerts deleted
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        count = db.query(EvaluationAlert).filter(
            EvaluationAlert.created_at < cutoff,
            EvaluationAlert.acknowledged == True
        ).delete()

        db.commit()
        logger.info(f"Cleared {count} old alerts")

        return count
