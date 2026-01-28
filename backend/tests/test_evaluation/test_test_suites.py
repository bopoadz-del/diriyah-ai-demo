"""Tests for individual test suites."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestLinkingTestSuite:
    """Tests for LinkingTestSuite."""

    def test_suite_initialization(self):
        """Test that LinkingTestSuite initializes correctly."""
        from backend.evaluation.test_suites.linking_tests import LinkingTestSuite

        suite = LinkingTestSuite()
        assert suite.suite_name == "linking"
        assert len(suite.test_cases) > 0

    def test_suite_has_test_cases(self):
        """Test that suite has test cases."""
        from backend.evaluation.test_suites.linking_tests import LinkingTestSuite

        suite = LinkingTestSuite()
        assert len(suite.test_cases) >= 10

    def test_simple_pattern_linking(self):
        """Test simple pattern linking."""
        from backend.evaluation.test_suites.linking_tests import LinkingTestSuite

        suite = LinkingTestSuite()
        result = suite._simple_pattern_linking("Concrete Grade C40, 500 cubic meters")

        assert "links" in result
        assert len(result["links"]) > 0
        assert result["links"][0]["id"] == "03300"


class TestExtractionTestSuite:
    """Tests for ExtractionTestSuite."""

    def test_suite_initialization(self):
        """Test that ExtractionTestSuite initializes correctly."""
        from backend.evaluation.test_suites.extraction_tests import ExtractionTestSuite

        suite = ExtractionTestSuite()
        assert suite.suite_name == "extraction"
        assert len(suite.test_cases) > 0

    def test_extraction_duration(self):
        """Test duration extraction."""
        from backend.evaluation.test_suites.extraction_tests import ExtractionTestSuite

        suite = ExtractionTestSuite()
        result = suite._perform_extraction(
            "The project shall be completed within 18 months."
        )

        entities = result.get("entities", [])
        duration_found = any(e.get("type") == "Duration" for e in entities)
        assert duration_found

    def test_extraction_payment_term(self):
        """Test payment term extraction."""
        from backend.evaluation.test_suites.extraction_tests import ExtractionTestSuite

        suite = ExtractionTestSuite()
        result = suite._perform_extraction(
            "Payment shall be made within 30 days of invoice."
        )

        entities = result.get("entities", [])
        payment_found = any(e.get("type") == "PaymentTerm" for e in entities)
        assert payment_found

    def test_extraction_money_amount(self):
        """Test money amount extraction."""
        from backend.evaluation.test_suites.extraction_tests import ExtractionTestSuite

        suite = ExtractionTestSuite()
        result = suite._perform_extraction(
            "The contract value is $5,000,000."
        )

        entities = result.get("entities", [])
        amount_found = any(e.get("type") == "Amount" for e in entities)
        assert amount_found


class TestPredictionTestSuite:
    """Tests for PredictionTestSuite."""

    def test_suite_initialization(self):
        """Test that PredictionTestSuite initializes correctly."""
        from backend.evaluation.test_suites.prediction_tests import PredictionTestSuite

        suite = PredictionTestSuite()
        assert suite.suite_name == "prediction"
        assert len(suite.test_cases) > 0

    def test_simple_delay_prediction(self):
        """Test simple delay prediction."""
        from backend.evaluation.test_suites.prediction_tests import PredictionTestSuite

        suite = PredictionTestSuite()
        result = suite._perform_prediction({
            "tasks": [
                {"id": 1, "planned_duration": 10, "actual_duration": 12, "progress": 1.0}
            ],
            "constraints": []
        })

        assert "delay_days" in result
        assert result["delay_days"] >= 0

    def test_constraint_factor_applied(self):
        """Test that constraints affect delay prediction."""
        from backend.evaluation.test_suites.prediction_tests import PredictionTestSuite

        suite = PredictionTestSuite()

        # Without constraints
        result_no_constraint = suite._perform_prediction({
            "tasks": [
                {"id": 1, "planned_duration": 10, "actual_duration": None, "progress": 0.5}
            ],
            "constraints": []
        })

        # With constraints
        result_with_constraint = suite._perform_prediction({
            "tasks": [
                {"id": 1, "planned_duration": 10, "actual_duration": None, "progress": 0.5}
            ],
            "constraints": ["weather_delay", "material_shortage"]
        })

        assert result_with_constraint["constraint_factor"] > result_no_constraint.get("constraint_factor", 1.0)


class TestRuntimeTestSuite:
    """Tests for RuntimeTestSuite."""

    def test_suite_initialization(self):
        """Test that RuntimeTestSuite initializes correctly."""
        from backend.evaluation.test_suites.runtime_tests import RuntimeTestSuite

        suite = RuntimeTestSuite()
        assert suite.suite_name == "runtime"
        assert len(suite.test_cases) > 0

    def test_simple_sum_execution(self):
        """Test simple sum calculation."""
        from backend.evaluation.test_suites.runtime_tests import RuntimeTestSuite

        suite = RuntimeTestSuite()
        result = suite._builtin_execute(
            "calculate the total quantity",
            {"items": [{"quantity": 100}, {"quantity": 200}]}
        )

        assert result.get("result") == 300

    def test_average_calculation(self):
        """Test average calculation."""
        from backend.evaluation.test_suites.runtime_tests import RuntimeTestSuite

        suite = RuntimeTestSuite()
        result = suite._builtin_execute(
            "calculate average progress",
            {"tasks": [{"progress": 0.5}, {"progress": 0.7}]}
        )

        assert result.get("result") == pytest.approx(0.6, rel=0.01)

    def test_percentage_calculation(self):
        """Test percentage calculation."""
        from backend.evaluation.test_suites.runtime_tests import RuntimeTestSuite

        suite = RuntimeTestSuite()
        result = suite._builtin_execute(
            "what percentage of budget is spent",
            {"budget": 1000, "spent": 500}
        )

        assert result.get("result") == 50.0


class TestPDPTestSuite:
    """Tests for PDPTestSuite."""

    def test_suite_initialization(self):
        """Test that PDPTestSuite initializes correctly."""
        from backend.evaluation.test_suites.pdp_tests import PDPTestSuite

        suite = PDPTestSuite()
        assert suite.suite_name == "pdp"
        assert len(suite.test_cases) > 0

    def test_admin_access_granted(self):
        """Test that admin role grants access."""
        from backend.evaluation.test_suites.pdp_tests import PDPTestSuite

        suite = PDPTestSuite()
        result = suite._builtin_evaluate({
            "user_role": "admin",
            "action": "delete"
        })

        assert result.get("decision") == True

    def test_viewer_write_denied(self):
        """Test that viewer role denies write."""
        from backend.evaluation.test_suites.pdp_tests import PDPTestSuite

        suite = PDPTestSuite()
        result = suite._builtin_evaluate({
            "user_role": "viewer",
            "action": "write"
        })

        assert result.get("decision") == False

    def test_ssn_detection(self):
        """Test SSN detection in content."""
        from backend.evaluation.test_suites.pdp_tests import PDPTestSuite

        suite = PDPTestSuite()
        result = suite._builtin_evaluate({
            "user_role": "admin",
            "action": "write",
            "content": "My SSN is 123-45-6789"
        })

        assert result.get("decision") == False
        assert "pii_ssn" in result.get("violations", [])

    def test_sql_injection_detection(self):
        """Test SQL injection detection."""
        from backend.evaluation.test_suites.pdp_tests import PDPTestSuite

        suite = PDPTestSuite()
        result = suite._builtin_evaluate({
            "user_role": "admin",
            "action": "execute",
            "content": "SELECT * FROM users; DROP TABLE users;"
        })

        assert result.get("decision") == False
        assert "sql_injection" in result.get("violations", [])

    def test_rate_limit_under(self):
        """Test rate limit under threshold."""
        from backend.evaluation.test_suites.pdp_tests import PDPTestSuite

        suite = PDPTestSuite()
        result = suite._builtin_evaluate({
            "request_count": 50,
            "limit": 100
        })

        assert result.get("decision") == True

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        from backend.evaluation.test_suites.pdp_tests import PDPTestSuite

        suite = PDPTestSuite()
        result = suite._builtin_evaluate({
            "request_count": 150,
            "limit": 100
        })

        assert result.get("decision") == False
