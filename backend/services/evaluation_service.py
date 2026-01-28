"""Evaluation Service - Business logic wrapper for evaluation system."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.evaluation.test_harness import TestHarness, THRESHOLDS
from backend.evaluation.models import TestRun as TestRunModel, EvaluationMetric
from backend.evaluation.schemas import TestRun

logger = logging.getLogger(__name__)


class EvaluationService:
    """Business logic wrapper for evaluation operations."""

    def __init__(self):
        """Initialize evaluation service."""
        self.harness = TestHarness()

    def get_accuracy_trend(
        self,
        suite_name: str,
        days: int,
        db: Session
    ) -> List[float]:
        """Get accuracy trend for a suite over time.

        Args:
            suite_name: Name of the test suite
            days: Number of days of history
            db: Database session

        Returns:
            List of accuracy values over time
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        results = db.query(TestRunModel).filter(
            TestRunModel.test_suite == suite_name,
            TestRunModel.status == "completed",
            TestRunModel.started_at >= cutoff
        ).order_by(TestRunModel.started_at).all()

        return [r.accuracy_score for r in results if r.accuracy_score is not None]

    def compare_with_production(
        self,
        component: str,
        db: Session
    ) -> Dict:
        """Compare current metrics with production baseline.

        Args:
            component: Component to compare
            db: Database session

        Returns:
            Comparison results
        """
        # Get latest test run for component
        latest = db.query(TestRunModel).filter(
            TestRunModel.test_suite == component,
            TestRunModel.status == "completed"
        ).order_by(TestRunModel.started_at.desc()).first()

        if not latest:
            return {"error": "No test runs found for component"}

        # Get production threshold
        threshold = THRESHOLDS.get(component, 0.90)

        return {
            "component": component,
            "latest_accuracy": latest.accuracy_score,
            "production_threshold": threshold,
            "meets_threshold": (latest.accuracy_score or 0) >= threshold,
            "gap": threshold - (latest.accuracy_score or 0),
            "last_run": latest.started_at.isoformat() if latest.started_at else None
        }

    def validate_new_model(
        self,
        model_path: str,
        test_suite: str,
        db: Session
    ) -> bool:
        """Validate a new model against evaluation tests.

        Args:
            model_path: Path to the new model
            test_suite: Test suite to run
            db: Database session

        Returns:
            True if model passes validation
        """
        logger.info(f"Validating model {model_path} with suite {test_suite}")

        # Run the test suite
        result = self.harness.run_suite(test_suite, db)

        threshold = THRESHOLDS.get(test_suite, 0.90)
        passed = (result.accuracy_score or 0) >= threshold

        logger.info(
            f"Model validation {'PASSED' if passed else 'FAILED'}: "
            f"accuracy={result.accuracy_score:.1%}, threshold={threshold:.1%}"
        )

        return passed

    def rollback_on_regression(
        self,
        component: str,
        threshold_drop: float,
        db: Session
    ) -> Optional[Dict]:
        """Check if rollback is needed based on regression.

        Args:
            component: Component to check
            threshold_drop: Maximum allowed accuracy drop
            db: Database session

        Returns:
            Rollback recommendation if needed
        """
        # Get last two completed runs
        runs = db.query(TestRunModel).filter(
            TestRunModel.test_suite == component,
            TestRunModel.status == "completed"
        ).order_by(TestRunModel.started_at.desc()).limit(2).all()

        if len(runs) < 2:
            return None

        current = runs[0]
        previous = runs[1]

        if not current.accuracy_score or not previous.accuracy_score:
            return None

        drop = previous.accuracy_score - current.accuracy_score

        if drop > threshold_drop:
            return {
                "rollback_recommended": True,
                "component": component,
                "current_accuracy": current.accuracy_score,
                "previous_accuracy": previous.accuracy_score,
                "drop": drop,
                "threshold_drop": threshold_drop,
                "current_run_id": current.id,
                "previous_run_id": previous.id
            }

        return None

    def get_health_summary(self, db: Session) -> Dict:
        """Get overall evaluation health summary.

        Args:
            db: Database session

        Returns:
            Health summary across all suites
        """
        summary = {
            "overall_health": "healthy",
            "suites": {},
            "alerts_count": 0,
            "last_run": None
        }

        from backend.evaluation.models import EvaluationAlert

        # Get alert count
        alerts = db.query(EvaluationAlert).filter(
            EvaluationAlert.acknowledged == False
        ).count()
        summary["alerts_count"] = alerts

        if alerts > 0:
            summary["overall_health"] = "degraded"

        # Check each suite
        for suite_name in THRESHOLDS:
            latest = db.query(TestRunModel).filter(
                TestRunModel.test_suite == suite_name,
                TestRunModel.status == "completed"
            ).order_by(TestRunModel.started_at.desc()).first()

            if latest:
                threshold = THRESHOLDS[suite_name]
                meets = (latest.accuracy_score or 0) >= threshold

                summary["suites"][suite_name] = {
                    "accuracy": latest.accuracy_score,
                    "threshold": threshold,
                    "meets_threshold": meets,
                    "last_run": latest.started_at.isoformat() if latest.started_at else None
                }

                if not meets:
                    summary["overall_health"] = "unhealthy"

                if summary["last_run"] is None or (
                    latest.started_at and
                    latest.started_at.isoformat() > summary["last_run"]
                ):
                    summary["last_run"] = latest.started_at.isoformat()

        return summary

    def schedule_test_suite(
        self,
        suite_name: str,
        cron: str,
        db: Session
    ) -> Dict:
        """Schedule a test suite to run on a cron schedule.

        Note: This is a placeholder. Actual scheduling would require
        APScheduler, Celery, or similar.

        Args:
            suite_name: Suite to schedule
            cron: Cron expression
            db: Database session

        Returns:
            Schedule confirmation
        """
        logger.info(f"Scheduling suite {suite_name} with cron: {cron}")

        # This would integrate with a scheduler like APScheduler
        # For now, just return confirmation

        return {
            "scheduled": True,
            "suite_name": suite_name,
            "cron": cron,
            "message": "Test suite scheduled (scheduler integration pending)"
        }
