"""Base class for test suites."""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..schemas import TestResult

logger = logging.getLogger(__name__)


class BaseTestSuite(ABC):
    """Base class for all test suites."""

    suite_name: str = "base"
    description: str = "Base test suite"

    def __init__(self):
        """Initialize test suite."""
        self.test_cases = self._load_test_cases()

    @abstractmethod
    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """Load test cases for this suite.

        Returns:
            List of test case dictionaries with:
            - test_name: Unique name
            - input: Input data
            - expected: Expected output
            - metadata: Optional metadata
        """
        pass

    @abstractmethod
    def _run_single_test(
        self,
        test_case: Dict[str, Any],
        db: Session
    ) -> TestResult:
        """Run a single test case.

        Args:
            test_case: Test case dictionary
            db: Database session

        Returns:
            TestResult with pass/fail status
        """
        pass

    def run_all_tests(self, db: Session) -> List[TestResult]:
        """Run all test cases in the suite.

        Args:
            db: Database session

        Returns:
            List of TestResult objects
        """
        results = []
        logger.info(f"Running {len(self.test_cases)} tests for {self.suite_name}")

        for test_case in self.test_cases:
            try:
                start_time = time.time()
                result = self._run_single_test(test_case, db)
                result.execution_time = time.time() - start_time
                results.append(result)

                status = "PASS" if result.passed else "FAIL"
                logger.debug(f"  {test_case.get('test_name', 'unknown')}: {status}")

            except Exception as e:
                logger.error(f"Test {test_case.get('test_name')} raised exception: {e}")
                results.append(TestResult(
                    id=0,
                    test_run_id=0,
                    test_name=test_case.get("test_name", "unknown"),
                    passed=False,
                    error_message=str(e),
                    expected_output=test_case.get("expected"),
                    actual_output=None,
                    execution_time=0,
                    created_at=None
                ))

        passed = sum(1 for r in results if r.passed)
        logger.info(f"Suite {self.suite_name}: {passed}/{len(results)} passed")

        return results

    def _compare_outputs(
        self,
        expected: Any,
        actual: Any,
        tolerance: float = 0.0
    ) -> bool:
        """Compare expected and actual outputs.

        Args:
            expected: Expected output
            actual: Actual output
            tolerance: Numeric tolerance for float comparisons

        Returns:
            True if outputs match
        """
        if expected is None and actual is None:
            return True

        if expected is None or actual is None:
            return False

        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return abs(expected - actual) <= tolerance

        if isinstance(expected, dict) and isinstance(actual, dict):
            return self._compare_dicts(expected, actual, tolerance)

        if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
            return self._compare_lists(expected, actual, tolerance)

        return expected == actual

    def _compare_dicts(
        self,
        expected: Dict,
        actual: Dict,
        tolerance: float = 0.0
    ) -> bool:
        """Compare dictionaries recursively."""
        if set(expected.keys()) != set(actual.keys()):
            return False

        for key in expected:
            if not self._compare_outputs(expected[key], actual[key], tolerance):
                return False

        return True

    def _compare_lists(
        self,
        expected: List,
        actual: List,
        tolerance: float = 0.0
    ) -> bool:
        """Compare lists."""
        if len(expected) != len(actual):
            return False

        for exp, act in zip(expected, actual):
            if not self._compare_outputs(exp, act, tolerance):
                return False

        return True
