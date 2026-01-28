"""Test Harness - Main orchestrator for evaluation system."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .models import TestRun as TestRunModel, TestResult as TestResultModel, EvaluationMetric
from .schemas import (
    TestRun, TestResult, EvaluationMetric as EvaluationMetricSchema,
    EvaluationReport, MetricType, MetricStatus, TestStatus
)
from .metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)


# Test suite definitions
TEST_SUITES = {
    "linking": "BOQ <-> Spec Linking",
    "extraction": "Contract Clause Extraction",
    "prediction": "Schedule Delay Prediction",
    "runtime": "Code Generation & Execution",
    "pdp": "Policy Decision Accuracy"
}

# Accuracy thresholds for each suite
THRESHOLDS = {
    "linking": 0.94,
    "extraction": 0.89,
    "prediction": 0.78,
    "runtime": 0.85,
    "pdp": 0.99
}


class TestHarness:
    """Main orchestrator for running evaluation tests."""

    def __init__(self):
        """Initialize test harness."""
        self.metrics_calculator = MetricsCalculator()
        self._test_suites = {}
        self._load_test_suites()

    def _load_test_suites(self):
        """Lazy load test suite implementations."""
        # Import here to avoid circular imports
        try:
            from .test_suites.linking_tests import LinkingTestSuite
            self._test_suites["linking"] = LinkingTestSuite()
        except ImportError as e:
            logger.warning(f"Could not load linking test suite: {e}")

        try:
            from .test_suites.extraction_tests import ExtractionTestSuite
            self._test_suites["extraction"] = ExtractionTestSuite()
        except ImportError as e:
            logger.warning(f"Could not load extraction test suite: {e}")

        try:
            from .test_suites.prediction_tests import PredictionTestSuite
            self._test_suites["prediction"] = PredictionTestSuite()
        except ImportError as e:
            logger.warning(f"Could not load prediction test suite: {e}")

        try:
            from .test_suites.runtime_tests import RuntimeTestSuite
            self._test_suites["runtime"] = RuntimeTestSuite()
        except ImportError as e:
            logger.warning(f"Could not load runtime test suite: {e}")

        try:
            from .test_suites.pdp_tests import PDPTestSuite
            self._test_suites["pdp"] = PDPTestSuite()
        except ImportError as e:
            logger.warning(f"Could not load PDP test suite: {e}")

    def run_suite(
        self,
        suite_name: str,
        db: Session,
        config: Optional[Dict] = None
    ) -> TestRun:
        """Run a specific test suite.

        Args:
            suite_name: Name of the suite (linking, extraction, etc.)
            db: Database session
            config: Optional configuration for the run

        Returns:
            TestRun with results
        """
        if suite_name not in TEST_SUITES:
            raise ValueError(f"Unknown test suite: {suite_name}. Valid suites: {list(TEST_SUITES.keys())}")

        logger.info(f"Starting test suite: {suite_name}")

        # Create test run record
        test_run = TestRunModel(
            test_suite=suite_name,
            status="running",
            config_json=config or {}
        )
        db.add(test_run)
        db.commit()
        db.refresh(test_run)

        try:
            # Get suite implementation
            suite = self._test_suites.get(suite_name)
            if not suite:
                raise ValueError(f"Test suite '{suite_name}' not loaded")

            # Run tests
            results = suite.run_all_tests(db)

            # Save results
            passed = 0
            for result in results:
                result_model = TestResultModel(
                    test_run_id=test_run.id,
                    test_name=result.test_name,
                    passed=result.passed,
                    actual_output_json=result.actual_output,
                    expected_output_json=result.expected_output,
                    error_message=result.error_message,
                    execution_time=result.execution_time
                )
                db.add(result_model)
                if result.passed:
                    passed += 1

            # Calculate metrics
            accuracy = self.metrics_calculator.calculate_accuracy(results)
            all_metrics = self.metrics_calculator.calculate_all_metrics(results)

            # Update test run
            test_run.status = "completed"
            test_run.completed_at = datetime.utcnow()
            test_run.total_tests = len(results)
            test_run.passed_tests = passed
            test_run.failed_tests = len(results) - passed
            test_run.accuracy_score = accuracy

            # Save metrics
            threshold = THRESHOLDS.get(suite_name, 0.90)
            for metric_name, value in all_metrics.items():
                metric_status = "pass" if value >= threshold else "fail"
                if value >= threshold * 0.95:
                    metric_status = "warn" if value < threshold else "pass"

                metric = EvaluationMetric(
                    metric_name=f"{suite_name}_{metric_name}",
                    metric_type=metric_name,
                    value=value,
                    threshold=threshold if metric_name == "accuracy" else None,
                    status=metric_status,
                    test_run_id=test_run.id
                )
                db.add(metric)

            db.commit()
            db.refresh(test_run)

            logger.info(
                f"Test suite {suite_name} completed: "
                f"{passed}/{len(results)} passed, accuracy: {accuracy:.1%}"
            )

        except Exception as e:
            logger.error(f"Test suite {suite_name} failed: {e}")
            test_run.status = "failed"
            test_run.completed_at = datetime.utcnow()
            db.commit()
            raise

        return TestRun.model_validate(test_run)

    def run_all_suites(
        self,
        db: Session,
        config: Optional[Dict] = None
    ) -> List[TestRun]:
        """Run all test suites.

        Args:
            db: Database session
            config: Optional configuration for runs

        Returns:
            List of TestRun results
        """
        results = []
        for suite_name in TEST_SUITES:
            try:
                result = self.run_suite(suite_name, db, config)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to run suite {suite_name}: {e}")
                # Create failed run record
                failed_run = TestRunModel(
                    test_suite=suite_name,
                    status="failed",
                    completed_at=datetime.utcnow(),
                    config_json={"error": str(e)}
                )
                db.add(failed_run)
                db.commit()
                results.append(TestRun.model_validate(failed_run))

        return results

    def calculate_metrics(
        self,
        test_run_id: int,
        db: Session
    ) -> List[EvaluationMetricSchema]:
        """Calculate metrics for a completed test run.

        Args:
            test_run_id: ID of the test run
            db: Database session

        Returns:
            List of calculated metrics
        """
        test_run = db.query(TestRunModel).filter(
            TestRunModel.id == test_run_id
        ).first()

        if not test_run:
            raise ValueError(f"Test run {test_run_id} not found")

        results = db.query(TestResultModel).filter(
            TestResultModel.test_run_id == test_run_id
        ).all()

        # Convert to schema objects
        result_schemas = [
            TestResult(
                id=r.id,
                test_run_id=r.test_run_id,
                test_case_id=r.test_case_id,
                test_name=r.test_name,
                passed=r.passed,
                actual_output=r.actual_output_json,
                expected_output=r.expected_output_json,
                error_message=r.error_message,
                execution_time=r.execution_time,
                created_at=r.created_at
            )
            for r in results
        ]

        all_metrics = self.metrics_calculator.calculate_all_metrics(result_schemas)
        threshold = THRESHOLDS.get(test_run.test_suite, 0.90)

        metric_schemas = []
        for metric_name, value in all_metrics.items():
            status = MetricStatus.PASS if value >= threshold else MetricStatus.FAIL
            metric_schemas.append(
                EvaluationMetricSchema(
                    metric_name=f"{test_run.test_suite}_{metric_name}",
                    metric_type=MetricType(metric_name),
                    value=value,
                    threshold=threshold if metric_name == "accuracy" else None,
                    status=status,
                    test_run_id=test_run_id,
                    timestamp=datetime.utcnow()
                )
            )

        return metric_schemas

    def compare_with_baseline(
        self,
        current_run_id: int,
        baseline_run_id: int,
        db: Session
    ) -> Dict:
        """Compare current run with a baseline.

        Args:
            current_run_id: ID of current test run
            baseline_run_id: ID of baseline test run
            db: Database session

        Returns:
            Comparison results
        """
        current = db.query(TestRunModel).filter(
            TestRunModel.id == current_run_id
        ).first()
        baseline = db.query(TestRunModel).filter(
            TestRunModel.id == baseline_run_id
        ).first()

        if not current or not baseline:
            raise ValueError("Test runs not found")

        accuracy_change = (
            (current.accuracy_score or 0) - (baseline.accuracy_score or 0)
        )

        return {
            "current_run_id": current_run_id,
            "baseline_run_id": baseline_run_id,
            "current_accuracy": current.accuracy_score,
            "baseline_accuracy": baseline.accuracy_score,
            "accuracy_change": accuracy_change,
            "accuracy_change_percent": (
                accuracy_change / baseline.accuracy_score * 100
                if baseline.accuracy_score else 0
            ),
            "improved": accuracy_change > 0,
            "regression": accuracy_change < -0.05,  # 5% drop is regression
            "current_passed": current.passed_tests,
            "baseline_passed": baseline.passed_tests,
            "current_total": current.total_tests,
            "baseline_total": baseline.total_tests
        }

    def generate_report(
        self,
        test_run_id: int,
        db: Session
    ) -> EvaluationReport:
        """Generate an evaluation report for a test run.

        Args:
            test_run_id: ID of the test run
            db: Database session

        Returns:
            EvaluationReport with summary, metrics, and recommendations
        """
        test_run = db.query(TestRunModel).filter(
            TestRunModel.id == test_run_id
        ).first()

        if not test_run:
            raise ValueError(f"Test run {test_run_id} not found")

        # Get results
        results = db.query(TestResultModel).filter(
            TestResultModel.test_run_id == test_run_id
        ).all()

        # Get failed tests
        failed_results = [r for r in results if not r.passed]
        failed_tests = [
            TestResult(
                id=r.id,
                test_run_id=r.test_run_id,
                test_case_id=r.test_case_id,
                test_name=r.test_name,
                passed=r.passed,
                actual_output=r.actual_output_json,
                expected_output=r.expected_output_json,
                error_message=r.error_message,
                execution_time=r.execution_time,
                created_at=r.created_at
            )
            for r in failed_results
        ]

        # Calculate metrics
        metrics = self.calculate_metrics(test_run_id, db)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            test_run.test_suite,
            test_run.accuracy_score or 0,
            failed_tests
        )

        # Build summary
        summary = {
            "test_suite": test_run.test_suite,
            "suite_name": TEST_SUITES.get(test_run.test_suite, test_run.test_suite),
            "status": test_run.status,
            "total_tests": test_run.total_tests,
            "passed_tests": test_run.passed_tests,
            "failed_tests": test_run.failed_tests,
            "accuracy": test_run.accuracy_score,
            "threshold": THRESHOLDS.get(test_run.test_suite, 0.90),
            "meets_threshold": (
                test_run.accuracy_score >= THRESHOLDS.get(test_run.test_suite, 0.90)
                if test_run.accuracy_score else False
            ),
            "duration_seconds": (
                (test_run.completed_at - test_run.started_at).total_seconds()
                if test_run.completed_at else None
            )
        }

        return EvaluationReport(
            test_run_id=test_run_id,
            test_suite=test_run.test_suite,
            summary=summary,
            metrics=metrics,
            failed_tests=failed_tests,
            recommendations=recommendations
        )

    def _generate_recommendations(
        self,
        suite_name: str,
        accuracy: float,
        failed_tests: List[TestResult]
    ) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        threshold = THRESHOLDS.get(suite_name, 0.90)

        if accuracy < threshold:
            gap = threshold - accuracy
            recommendations.append(
                f"Accuracy ({accuracy:.1%}) is below threshold ({threshold:.1%}). "
                f"Need to improve by {gap:.1%} to meet target."
            )

        if failed_tests:
            # Group failures by type
            error_types = {}
            for test in failed_tests:
                error_type = "unknown"
                if test.error_message:
                    if "not found" in test.error_message.lower():
                        error_type = "missing_match"
                    elif "incorrect" in test.error_message.lower():
                        error_type = "wrong_match"
                    elif "timeout" in test.error_message.lower():
                        error_type = "timeout"

                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in error_types.items():
                if error_type == "missing_match":
                    recommendations.append(
                        f"{count} tests failed due to missing matches. "
                        "Consider expanding pattern coverage or training data."
                    )
                elif error_type == "wrong_match":
                    recommendations.append(
                        f"{count} tests produced incorrect matches. "
                        "Review matching thresholds and validation logic."
                    )
                elif error_type == "timeout":
                    recommendations.append(
                        f"{count} tests timed out. "
                        "Consider optimizing performance or increasing timeout."
                    )

        if not recommendations:
            recommendations.append(
                f"All tests passing with {accuracy:.1%} accuracy. "
                "Consider adding more test cases for edge cases."
            )

        return recommendations
