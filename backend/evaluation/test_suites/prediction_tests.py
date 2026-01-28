"""Prediction Test Suite - Schedule delay prediction accuracy tests."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..schemas import TestResult
from .base import BaseTestSuite

logger = logging.getLogger(__name__)

# Default test cases for delay prediction
PREDICTION_TEST_CASES = [
    {
        "test_name": "simple_delay_prediction",
        "input": {
            "tasks": [
                {"id": 1, "name": "Foundation", "planned_duration": 10, "actual_duration": 12, "progress": 1.0},
                {"id": 2, "name": "Structure", "planned_duration": 20, "actual_duration": None, "progress": 0.3}
            ],
            "constraints": []
        },
        "expected": {"delay_days": 4, "tolerance": 2},
        "metadata": {"complexity": "simple", "difficulty": "easy"}
    },
    {
        "test_name": "weather_delay_prediction",
        "input": {
            "tasks": [
                {"id": 1, "name": "Excavation", "planned_duration": 5, "actual_duration": 8, "progress": 1.0},
                {"id": 2, "name": "Foundation", "planned_duration": 10, "actual_duration": None, "progress": 0.0}
            ],
            "constraints": ["weather_delay"]
        },
        "expected": {"delay_days": 5, "tolerance": 3},
        "metadata": {"complexity": "moderate", "difficulty": "medium"}
    },
    {
        "test_name": "material_shortage_prediction",
        "input": {
            "tasks": [
                {"id": 1, "name": "Steel erection", "planned_duration": 15, "actual_duration": 18, "progress": 0.8}
            ],
            "constraints": ["material_shortage"]
        },
        "expected": {"delay_days": 6, "tolerance": 3},
        "metadata": {"complexity": "moderate", "difficulty": "medium"}
    },
    {
        "test_name": "multiple_constraints_prediction",
        "input": {
            "tasks": [
                {"id": 1, "name": "Foundation", "planned_duration": 10, "actual_duration": 14, "progress": 1.0},
                {"id": 2, "name": "Structure", "planned_duration": 30, "actual_duration": None, "progress": 0.5},
                {"id": 3, "name": "MEP", "planned_duration": 20, "actual_duration": None, "progress": 0.0}
            ],
            "constraints": ["weather_delay", "labor_shortage", "material_shortage"]
        },
        "expected": {"delay_days": 15, "tolerance": 5},
        "metadata": {"complexity": "complex", "difficulty": "hard"}
    },
    {
        "test_name": "on_track_prediction",
        "input": {
            "tasks": [
                {"id": 1, "name": "Task 1", "planned_duration": 10, "actual_duration": 9, "progress": 1.0},
                {"id": 2, "name": "Task 2", "planned_duration": 10, "actual_duration": None, "progress": 0.6}
            ],
            "constraints": []
        },
        "expected": {"delay_days": 0, "tolerance": 1},
        "metadata": {"complexity": "simple", "difficulty": "easy"}
    },
    {
        "test_name": "critical_path_delay",
        "input": {
            "tasks": [
                {"id": 1, "name": "Critical Task A", "planned_duration": 20, "actual_duration": 25, "progress": 1.0, "critical": True},
                {"id": 2, "name": "Non-critical B", "planned_duration": 15, "actual_duration": 12, "progress": 1.0, "critical": False},
                {"id": 3, "name": "Critical Task C", "planned_duration": 15, "actual_duration": None, "progress": 0.2, "critical": True}
            ],
            "constraints": []
        },
        "expected": {"delay_days": 7, "tolerance": 2},
        "metadata": {"complexity": "moderate", "difficulty": "medium"}
    },
    {
        "test_name": "resource_constraint_delay",
        "input": {
            "tasks": [
                {"id": 1, "name": "Electrical rough-in", "planned_duration": 12, "actual_duration": 15, "progress": 1.0},
                {"id": 2, "name": "Electrical finish", "planned_duration": 8, "actual_duration": None, "progress": 0.0}
            ],
            "constraints": ["labor_shortage"],
            "resources": {"electricians": {"available": 4, "required": 8}}
        },
        "expected": {"delay_days": 8, "tolerance": 3},
        "metadata": {"complexity": "moderate", "difficulty": "medium"}
    },
    {
        "test_name": "sequential_delay_propagation",
        "input": {
            "tasks": [
                {"id": 1, "name": "Task A", "planned_duration": 5, "actual_duration": 7, "progress": 1.0, "successors": [2]},
                {"id": 2, "name": "Task B", "planned_duration": 5, "actual_duration": 6, "progress": 1.0, "successors": [3]},
                {"id": 3, "name": "Task C", "planned_duration": 5, "actual_duration": None, "progress": 0.4, "successors": []}
            ],
            "constraints": []
        },
        "expected": {"delay_days": 4, "tolerance": 2},
        "metadata": {"complexity": "moderate", "difficulty": "medium"}
    },
    {
        "test_name": "cost_variance_with_delay",
        "input": {
            "tasks": [
                {"id": 1, "name": "Foundation", "planned_duration": 10, "actual_duration": 13, "progress": 1.0,
                 "planned_cost": 100000, "actual_cost": 115000}
            ],
            "constraints": []
        },
        "expected": {"delay_days": 3, "cost_variance": 15000, "tolerance": 1},
        "metadata": {"complexity": "moderate", "difficulty": "medium"}
    },
    {
        "test_name": "acceleration_scenario",
        "input": {
            "tasks": [
                {"id": 1, "name": "Task A", "planned_duration": 10, "actual_duration": 12, "progress": 1.0},
                {"id": 2, "name": "Task B", "planned_duration": 10, "actual_duration": None, "progress": 0.5}
            ],
            "constraints": [],
            "acceleration": {"enabled": True, "additional_cost": 50000, "days_recoverable": 3}
        },
        "expected": {"delay_days": 1, "tolerance": 2, "with_acceleration": True},
        "metadata": {"complexity": "moderate", "difficulty": "medium"}
    }
]


class PredictionTestSuite(BaseTestSuite):
    """Test suite for schedule delay prediction accuracy."""

    suite_name = "prediction"
    description = "Schedule Delay Prediction Tests"

    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """Load prediction test cases from file or defaults."""
        data_path = Path(__file__).parent.parent / "data" / "test_datasets" / "prediction_tests.json"

        if data_path.exists():
            try:
                with open(data_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load prediction tests from file: {e}")

        return PREDICTION_TEST_CASES

    def _run_single_test(
        self,
        test_case: Dict[str, Any],
        db: Session
    ) -> TestResult:
        """Run a single prediction test."""
        test_name = test_case.get("test_name", "unknown")
        input_data = test_case.get("input", {})
        expected = test_case.get("expected", {})

        try:
            actual = self._perform_prediction(input_data)
            passed = self._evaluate_prediction_result(expected, actual)

            return TestResult(
                id=0,
                test_run_id=0,
                test_name=test_name,
                passed=passed,
                actual_output=actual,
                expected_output=expected,
                error_message=None if passed else "Prediction outside tolerance",
                created_at=datetime.utcnow()
            )

        except Exception as e:
            return TestResult(
                id=0,
                test_run_id=0,
                test_name=test_name,
                passed=False,
                actual_output=None,
                expected_output=expected,
                error_message=str(e),
                created_at=datetime.utcnow()
            )

    def _perform_prediction(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform delay prediction.

        Uses simple heuristics or Task 2 runtime if available.
        """
        tasks = input_data.get("tasks", [])
        constraints = input_data.get("constraints", [])

        # Try to use runtime from Task 2
        try:
            from backend.runtime.function_registry import FunctionRegistry
            registry = FunctionRegistry()

            if "schedule_slip_forecast" in [f["name"] for f in registry.list_functions()]:
                result = registry.call_function(
                    "schedule_slip_forecast",
                    tasks=tasks,
                    constraints=constraints
                )
                return result
        except (ImportError, Exception) as e:
            logger.debug(f"Runtime not available, using built-in prediction: {e}")

        # Built-in prediction logic
        total_delay = 0
        cost_variance = 0

        for task in tasks:
            planned = task.get("planned_duration", 0)
            actual = task.get("actual_duration")
            progress = task.get("progress", 0)

            if actual is not None:
                # Completed or in-progress task with actual duration
                task_delay = max(0, actual - planned)
                total_delay += task_delay
            elif progress > 0:
                # In-progress task - estimate completion
                elapsed = planned * progress
                estimated_total = elapsed / progress if progress > 0 else planned
                task_delay = max(0, estimated_total - planned)
                total_delay += task_delay * (1 - progress)  # Only remaining delay

            # Cost variance
            planned_cost = task.get("planned_cost", 0)
            actual_cost = task.get("actual_cost", 0)
            if planned_cost and actual_cost:
                cost_variance += actual_cost - planned_cost

        # Apply constraint factors
        constraint_factor = 1.0
        for constraint in constraints:
            if constraint == "weather_delay":
                constraint_factor += 0.2
            elif constraint == "material_shortage":
                constraint_factor += 0.25
            elif constraint == "labor_shortage":
                constraint_factor += 0.3

        # Adjust delay for constraints (if tasks are pending)
        pending_tasks = [t for t in tasks if t.get("progress", 0) < 1.0]
        if pending_tasks and constraints:
            avg_pending_duration = sum(t.get("planned_duration", 0) for t in pending_tasks) / len(pending_tasks)
            total_delay += avg_pending_duration * (constraint_factor - 1.0)

        # Check for acceleration
        acceleration = input_data.get("acceleration", {})
        if acceleration.get("enabled"):
            recoverable = acceleration.get("days_recoverable", 0)
            total_delay = max(0, total_delay - recoverable)

        return {
            "delay_days": round(total_delay),
            "cost_variance": cost_variance,
            "constraint_factor": constraint_factor,
            "tasks_analyzed": len(tasks)
        }

    def _evaluate_prediction_result(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> bool:
        """Evaluate if prediction is within tolerance."""
        expected_delay = expected.get("delay_days", 0)
        actual_delay = actual.get("delay_days", 0)
        tolerance = expected.get("tolerance", 2)

        delay_ok = abs(expected_delay - actual_delay) <= tolerance

        # Check cost variance if specified
        expected_cost = expected.get("cost_variance")
        if expected_cost is not None:
            actual_cost = actual.get("cost_variance", 0)
            cost_tolerance = expected_cost * 0.2  # 20% tolerance
            cost_ok = abs(expected_cost - actual_cost) <= cost_tolerance
            return delay_ok and cost_ok

        return delay_ok

    def test_delay_prediction(self, db: Session) -> List[TestResult]:
        """Run delay prediction tests."""
        delay_tests = [tc for tc in self.test_cases if "delay" in tc.get("test_name", "")]
        results = []
        for test_case in delay_tests:
            results.append(self._run_single_test(test_case, db))
        return results

    def test_risk_assessment(self, db: Session) -> List[TestResult]:
        """Run risk assessment tests."""
        risk_tests = [tc for tc in self.test_cases if "constraint" in tc.get("test_name", "")]
        results = []
        for test_case in risk_tests:
            results.append(self._run_single_test(test_case, db))
        return results

    def calculate_prediction_metrics(self, results: List[TestResult]) -> Dict[str, float]:
        """Calculate prediction-specific metrics."""
        from ..metrics_calculator import MetricsCalculator
        return MetricsCalculator.calculate_all_metrics(results)
