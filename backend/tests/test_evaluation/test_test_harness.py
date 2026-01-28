"""Tests for TestHarness class."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from backend.evaluation.test_harness import TestHarness, TEST_SUITES, THRESHOLDS
from backend.evaluation.schemas import TestRun, TestResult


class TestTestHarness:
    """Tests for TestHarness."""

    def test_test_suites_defined(self):
        """Test that all test suites are defined."""
        assert "linking" in TEST_SUITES
        assert "extraction" in TEST_SUITES
        assert "prediction" in TEST_SUITES
        assert "runtime" in TEST_SUITES
        assert "pdp" in TEST_SUITES

    def test_thresholds_defined(self):
        """Test that thresholds are defined for all suites."""
        assert THRESHOLDS["linking"] == 0.94
        assert THRESHOLDS["extraction"] == 0.89
        assert THRESHOLDS["prediction"] == 0.78
        assert THRESHOLDS["runtime"] == 0.85
        assert THRESHOLDS["pdp"] == 0.99

    def test_harness_initialization(self):
        """Test TestHarness initializes correctly."""
        harness = TestHarness()
        assert harness is not None
        assert harness.metrics_calculator is not None

    def test_run_suite_invalid_name(self):
        """Test that invalid suite name raises error."""
        harness = TestHarness()
        mock_db = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            harness.run_suite("invalid_suite", mock_db)

        assert "Unknown test suite" in str(exc_info.value)

    @patch('backend.evaluation.test_harness.TestHarness._load_test_suites')
    def test_run_suite_creates_test_run(self, mock_load):
        """Test that running a suite creates a test run record."""
        harness = TestHarness()
        mock_db = MagicMock()

        # Mock the test suite
        mock_suite = MagicMock()
        mock_suite.run_all_tests.return_value = [
            TestResult(
                id=1,
                test_run_id=1,
                test_name="test1",
                passed=True,
                created_at=datetime.utcnow()
            )
        ]
        harness._test_suites["linking"] = mock_suite

        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Create a mock test run that gets returned
        mock_test_run = MagicMock()
        mock_test_run.id = 1
        mock_test_run.test_suite = "linking"
        mock_test_run.status = "completed"
        mock_test_run.started_at = datetime.utcnow()
        mock_test_run.completed_at = datetime.utcnow()
        mock_test_run.total_tests = 1
        mock_test_run.passed_tests = 1
        mock_test_run.failed_tests = 0
        mock_test_run.accuracy_score = 1.0
        mock_test_run.config_json = {}

        # Make db.add capture the model and refresh returns it
        def capture_add(obj):
            if hasattr(obj, 'test_suite'):
                obj.id = 1
        mock_db.add.side_effect = capture_add

        def refresh_obj(obj):
            if hasattr(obj, 'test_suite'):
                obj.id = 1
                obj.status = "completed"
                obj.total_tests = 1
                obj.passed_tests = 1
                obj.failed_tests = 0
                obj.accuracy_score = 1.0
                obj.started_at = datetime.utcnow()
                obj.completed_at = datetime.utcnow()
                obj.config_json = {}
        mock_db.refresh.side_effect = refresh_obj

        result = harness.run_suite("linking", mock_db)

        assert mock_db.add.called
        assert mock_db.commit.called


class TestMetricsCalculator:
    """Tests for MetricsCalculator."""

    def test_calculate_accuracy_all_passed(self):
        """Test accuracy calculation when all tests pass."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        results = [
            TestResult(id=1, test_run_id=1, test_name="t1", passed=True, created_at=datetime.utcnow()),
            TestResult(id=2, test_run_id=1, test_name="t2", passed=True, created_at=datetime.utcnow()),
        ]

        accuracy = MetricsCalculator.calculate_accuracy(results)
        assert accuracy == 1.0

    def test_calculate_accuracy_half_passed(self):
        """Test accuracy calculation when half tests pass."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        results = [
            TestResult(id=1, test_run_id=1, test_name="t1", passed=True, created_at=datetime.utcnow()),
            TestResult(id=2, test_run_id=1, test_name="t2", passed=False, created_at=datetime.utcnow()),
        ]

        accuracy = MetricsCalculator.calculate_accuracy(results)
        assert accuracy == 0.5

    def test_calculate_accuracy_none_passed(self):
        """Test accuracy calculation when no tests pass."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        results = [
            TestResult(id=1, test_run_id=1, test_name="t1", passed=False, created_at=datetime.utcnow()),
            TestResult(id=2, test_run_id=1, test_name="t2", passed=False, created_at=datetime.utcnow()),
        ]

        accuracy = MetricsCalculator.calculate_accuracy(results)
        assert accuracy == 0.0

    def test_calculate_accuracy_empty_list(self):
        """Test accuracy calculation with empty list."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        accuracy = MetricsCalculator.calculate_accuracy([])
        assert accuracy == 0.0

    def test_calculate_precision(self):
        """Test precision calculation."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        precision = MetricsCalculator.calculate_precision(8, 2)
        assert precision == 0.8

    def test_calculate_recall(self):
        """Test recall calculation."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        recall = MetricsCalculator.calculate_recall(8, 2)
        assert recall == 0.8

    def test_calculate_f1_score(self):
        """Test F1 score calculation."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        f1 = MetricsCalculator.calculate_f1_score(0.8, 0.8)
        assert f1 == pytest.approx(0.8, rel=0.001)

    def test_calculate_f1_score_zero_values(self):
        """Test F1 score with zero precision and recall."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        f1 = MetricsCalculator.calculate_f1_score(0.0, 0.0)
        assert f1 == 0.0

    def test_calculate_all_metrics(self):
        """Test all metrics calculation."""
        from backend.evaluation.metrics_calculator import MetricsCalculator

        results = [
            TestResult(id=1, test_run_id=1, test_name="t1", passed=True, created_at=datetime.utcnow()),
            TestResult(id=2, test_run_id=1, test_name="t2", passed=True, created_at=datetime.utcnow()),
            TestResult(id=3, test_run_id=1, test_name="t3", passed=False, created_at=datetime.utcnow()),
        ]

        metrics = MetricsCalculator.calculate_all_metrics(results)

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert metrics["accuracy"] == pytest.approx(0.667, rel=0.01)
