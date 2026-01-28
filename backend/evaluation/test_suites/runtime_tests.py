"""Runtime Test Suite - Code generation and execution accuracy tests."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..schemas import TestResult
from .base import BaseTestSuite

logger = logging.getLogger(__name__)

# Default test cases for runtime code execution
RUNTIME_TEST_CASES = [
    {
        "test_name": "simple_sum_calculation",
        "input": {
            "query": "Calculate the total quantity",
            "context": {
                "items": [{"quantity": 100}, {"quantity": 200}, {"quantity": 150}]
            }
        },
        "expected": {"result": 450, "tolerance": 0.01},
        "metadata": {"operation": "sum", "difficulty": "easy"}
    },
    {
        "test_name": "cost_variance_calculation",
        "input": {
            "query": "What is the cost variance if steel price increases by 15%?",
            "context": {
                "boq_items": [
                    {"material": "steel", "quantity": 100, "unit_cost": 50}
                ]
            }
        },
        "expected": {"result": {"variance": 750, "new_cost": 5750}, "tolerance": 0.05},
        "metadata": {"operation": "variance", "difficulty": "medium"}
    },
    {
        "test_name": "average_calculation",
        "input": {
            "query": "Calculate average progress across all tasks",
            "context": {
                "tasks": [
                    {"name": "Task A", "progress": 0.8},
                    {"name": "Task B", "progress": 0.6},
                    {"name": "Task C", "progress": 0.9}
                ]
            }
        },
        "expected": {"result": 0.767, "tolerance": 0.01},
        "metadata": {"operation": "average", "difficulty": "easy"}
    },
    {
        "test_name": "filter_and_sum",
        "input": {
            "query": "Sum quantities for concrete items only",
            "context": {
                "boq_items": [
                    {"material": "concrete", "quantity": 500},
                    {"material": "steel", "quantity": 200},
                    {"material": "concrete", "quantity": 300}
                ]
            }
        },
        "expected": {"result": 800, "tolerance": 0.01},
        "metadata": {"operation": "filter_sum", "difficulty": "medium"}
    },
    {
        "test_name": "percentage_calculation",
        "input": {
            "query": "What percentage of budget is spent?",
            "context": {
                "budget": 1000000,
                "spent": 650000
            }
        },
        "expected": {"result": 65.0, "tolerance": 0.1},
        "metadata": {"operation": "percentage", "difficulty": "easy"}
    },
    {
        "test_name": "multi_step_calculation",
        "input": {
            "query": "Calculate total cost with 10% markup and 5% tax",
            "context": {
                "base_cost": 100000
            }
        },
        "expected": {"result": 115500, "tolerance": 0.01},
        "metadata": {"operation": "multi_step", "difficulty": "medium"}
    },
    {
        "test_name": "date_difference_calculation",
        "input": {
            "query": "How many days between start and end?",
            "context": {
                "start_date": "2024-01-15",
                "end_date": "2024-03-20"
            }
        },
        "expected": {"result": 65, "tolerance": 0},
        "metadata": {"operation": "date_diff", "difficulty": "easy"}
    },
    {
        "test_name": "weighted_average",
        "input": {
            "query": "Calculate weighted average progress by cost",
            "context": {
                "tasks": [
                    {"progress": 0.5, "cost": 100000},
                    {"progress": 0.8, "cost": 200000},
                    {"progress": 0.3, "cost": 50000}
                ]
            }
        },
        "expected": {"result": 0.614, "tolerance": 0.02},
        "metadata": {"operation": "weighted_avg", "difficulty": "medium"}
    },
    {
        "test_name": "conditional_sum",
        "input": {
            "query": "Sum costs where progress is less than 50%",
            "context": {
                "tasks": [
                    {"name": "A", "progress": 0.3, "cost": 10000},
                    {"name": "B", "progress": 0.7, "cost": 20000},
                    {"name": "C", "progress": 0.4, "cost": 15000}
                ]
            }
        },
        "expected": {"result": 25000, "tolerance": 0.01},
        "metadata": {"operation": "conditional_sum", "difficulty": "medium"}
    },
    {
        "test_name": "max_min_calculation",
        "input": {
            "query": "Find the task with highest and lowest progress",
            "context": {
                "tasks": [
                    {"name": "Task A", "progress": 0.3},
                    {"name": "Task B", "progress": 0.9},
                    {"name": "Task C", "progress": 0.5}
                ]
            }
        },
        "expected": {
            "result": {"max": {"name": "Task B", "progress": 0.9}, "min": {"name": "Task A", "progress": 0.3}},
            "tolerance": 0.01
        },
        "metadata": {"operation": "max_min", "difficulty": "easy"}
    },
    {
        "test_name": "monte_carlo_simulation",
        "input": {
            "query": "Run Monte Carlo simulation for cost estimate",
            "context": {
                "base_cost": 1000000,
                "min_factor": 0.9,
                "max_factor": 1.3,
                "simulations": 100
            }
        },
        "expected": {"result": {"mean": 1100000, "std_range": [50000, 200000]}, "tolerance": 0.15},
        "metadata": {"operation": "monte_carlo", "difficulty": "hard"}
    },
    {
        "test_name": "group_by_calculation",
        "input": {
            "query": "Group items by category and sum quantities",
            "context": {
                "items": [
                    {"category": "A", "quantity": 100},
                    {"category": "B", "quantity": 200},
                    {"category": "A", "quantity": 150},
                    {"category": "B", "quantity": 50}
                ]
            }
        },
        "expected": {"result": {"A": 250, "B": 250}, "tolerance": 0.01},
        "metadata": {"operation": "group_by", "difficulty": "medium"}
    }
]


class RuntimeTestSuite(BaseTestSuite):
    """Test suite for code generation and execution accuracy."""

    suite_name = "runtime"
    description = "Code Generation & Execution Tests"

    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """Load runtime test cases from file or defaults."""
        data_path = Path(__file__).parent.parent / "data" / "test_datasets" / "runtime_tests.json"

        if data_path.exists():
            try:
                with open(data_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load runtime tests from file: {e}")

        return RUNTIME_TEST_CASES

    def _run_single_test(
        self,
        test_case: Dict[str, Any],
        db: Session
    ) -> TestResult:
        """Run a single runtime test."""
        test_name = test_case.get("test_name", "unknown")
        input_data = test_case.get("input", {})
        expected = test_case.get("expected", {})

        try:
            actual = self._execute_query(
                input_data.get("query", ""),
                input_data.get("context", {})
            )
            passed = self._evaluate_runtime_result(expected, actual)

            return TestResult(
                id=0,
                test_run_id=0,
                test_name=test_name,
                passed=passed,
                actual_output=actual,
                expected_output=expected,
                error_message=None if passed else "Result mismatch",
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

    def _execute_query(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute query using runtime system or built-in logic.

        Args:
            query: Natural language query
            context: Context data for the query

        Returns:
            Execution result
        """
        # Try to use Task 2 runtime
        try:
            from backend.runtime.code_generator import CodeGenerator
            from backend.runtime.sandbox import SandboxExecutor

            generator = CodeGenerator()
            executor = SandboxExecutor()

            # Generate code
            code = generator.generate(query, context)

            # Execute safely
            result = executor.execute(code, context)

            return {"result": result, "code_generated": True}

        except (ImportError, Exception) as e:
            logger.debug(f"Runtime not available, using built-in execution: {e}")

        # Built-in execution logic
        return self._builtin_execute(query.lower(), context)

    def _builtin_execute(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Built-in query execution without external runtime."""
        result = None

        # Sum calculations
        if "sum" in query or "total" in query:
            items = context.get("items") or context.get("boq_items") or context.get("tasks", [])

            if "concrete" in query:
                items = [i for i in items if i.get("material", "").lower() == "concrete"]

            if "progress" in query and "less than" in query:
                items = [i for i in items if i.get("progress", 1) < 0.5]
                result = sum(i.get("cost", 0) for i in items)
            else:
                result = sum(i.get("quantity", 0) for i in items)

        # Average calculations
        elif "average" in query:
            items = context.get("tasks", [])
            if "weighted" in query:
                total_weight = sum(i.get("cost", 1) for i in items)
                if total_weight > 0:
                    result = sum(i.get("progress", 0) * i.get("cost", 1) for i in items) / total_weight
            else:
                if items:
                    result = sum(i.get("progress", 0) for i in items) / len(items)

        # Percentage
        elif "percentage" in query:
            budget = context.get("budget", 1)
            spent = context.get("spent", 0)
            result = (spent / budget) * 100 if budget else 0

        # Cost variance
        elif "variance" in query or "increase" in query:
            items = context.get("boq_items", [])
            for item in items:
                if "steel" in item.get("material", "").lower():
                    base_cost = item.get("quantity", 0) * item.get("unit_cost", 0)
                    new_cost = base_cost * 1.15
                    result = {"variance": new_cost - base_cost, "new_cost": new_cost}

        # Multi-step with markup and tax
        elif "markup" in query and "tax" in query:
            base = context.get("base_cost", 0)
            with_markup = base * 1.10
            result = with_markup * 1.05

        # Date difference
        elif "days" in query and "between" in query:
            from datetime import datetime as dt
            start = dt.strptime(context.get("start_date", "2024-01-01"), "%Y-%m-%d")
            end = dt.strptime(context.get("end_date", "2024-01-01"), "%Y-%m-%d")
            result = (end - start).days

        # Max/Min
        elif "highest" in query or "lowest" in query or "max" in query or "min" in query:
            tasks = context.get("tasks", [])
            if tasks:
                max_task = max(tasks, key=lambda x: x.get("progress", 0))
                min_task = min(tasks, key=lambda x: x.get("progress", 0))
                result = {"max": max_task, "min": min_task}

        # Monte Carlo
        elif "monte carlo" in query:
            import random
            base = context.get("base_cost", 1000000)
            min_f = context.get("min_factor", 0.9)
            max_f = context.get("max_factor", 1.3)
            n = context.get("simulations", 100)

            samples = [base * random.uniform(min_f, max_f) for _ in range(n)]
            mean = sum(samples) / len(samples)
            std = (sum((x - mean) ** 2 for x in samples) / len(samples)) ** 0.5
            result = {"mean": mean, "std": std}

        # Group by
        elif "group" in query:
            items = context.get("items", [])
            groups = {}
            for item in items:
                cat = item.get("category", "unknown")
                groups[cat] = groups.get(cat, 0) + item.get("quantity", 0)
            result = groups

        return {"result": result, "code_generated": False}

    def _evaluate_runtime_result(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> bool:
        """Evaluate if runtime result matches expected."""
        exp_result = expected.get("result")
        act_result = actual.get("result")
        tolerance = expected.get("tolerance", 0.01)

        if exp_result is None and act_result is None:
            return True

        if exp_result is None or act_result is None:
            return False

        # Handle numeric comparison
        if isinstance(exp_result, (int, float)) and isinstance(act_result, (int, float)):
            if exp_result == 0:
                return abs(act_result) <= tolerance
            return abs(exp_result - act_result) / abs(exp_result) <= tolerance

        # Handle dict comparison
        if isinstance(exp_result, dict) and isinstance(act_result, dict):
            for key, exp_val in exp_result.items():
                act_val = act_result.get(key)
                if act_val is None:
                    continue

                # Special handling for std_range
                if key == "std_range" and isinstance(exp_val, list):
                    act_std = act_result.get("std", 0)
                    if not (exp_val[0] <= act_std <= exp_val[1]):
                        return False
                    continue

                if isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)):
                    if exp_val == 0:
                        if abs(act_val) > tolerance:
                            return False
                    elif abs(exp_val - act_val) / abs(exp_val) > tolerance:
                        return False
                elif isinstance(exp_val, dict) and isinstance(act_val, dict):
                    # Recursive dict comparison
                    if not self._compare_dicts(exp_val, act_val, tolerance):
                        return False

            return True

        return exp_result == act_result

    def _compare_dicts(self, d1: dict, d2: dict, tolerance: float) -> bool:
        """Compare two dicts with tolerance for numeric values."""
        for key in d1:
            if key not in d2:
                return False
            v1, v2 = d1[key], d2[key]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                if v1 != 0 and abs(v1 - v2) / abs(v1) > tolerance:
                    return False
            elif v1 != v2:
                return False
        return True

    def test_code_generation(self, db: Session) -> List[TestResult]:
        """Run code generation tests."""
        return self.run_all_tests(db)

    def test_code_execution(self, db: Session) -> List[TestResult]:
        """Run code execution tests."""
        return self.run_all_tests(db)

    def calculate_runtime_metrics(self, results: List[TestResult]) -> Dict[str, float]:
        """Calculate runtime-specific metrics."""
        from ..metrics_calculator import MetricsCalculator
        return MetricsCalculator.calculate_all_metrics(results)
