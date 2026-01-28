"""Benchmark Runner - Run performance benchmarks."""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .models import BenchmarkResult as BenchmarkResultModel
from .schemas import BenchmarkResult
from .test_harness import TEST_SUITES

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Run performance benchmarks for evaluation components."""

    def run_benchmarks(
        self,
        components: List[str],
        sample_size: int,
        db: Session
    ) -> List[BenchmarkResult]:
        """Run benchmarks for specified components.

        Args:
            components: List of components to benchmark
            sample_size: Number of samples per benchmark
            db: Database session

        Returns:
            List of benchmark results
        """
        results = []

        for component in components:
            if component not in TEST_SUITES:
                logger.warning(f"Unknown component: {component}")
                continue

            try:
                logger.info(f"Running benchmark for {component} with {sample_size} samples")
                result = self._run_component_benchmark(component, sample_size, db)
                results.append(result)
            except Exception as e:
                logger.error(f"Benchmark failed for {component}: {e}")

        return results

    def _run_component_benchmark(
        self,
        component: str,
        sample_size: int,
        db: Session
    ) -> BenchmarkResult:
        """Run benchmark for a single component.

        Args:
            component: Component to benchmark
            sample_size: Number of samples
            db: Database session

        Returns:
            BenchmarkResult
        """
        # Load the appropriate test suite
        suite = self._get_suite(component)
        test_cases = suite.test_cases[:sample_size] if suite else []

        if not test_cases:
            # Generate synthetic test cases
            test_cases = self._generate_synthetic_tests(component, sample_size)

        # Run benchmark
        start_time = time.time()
        passed = 0
        total = 0

        for test_case in test_cases:
            try:
                result = suite._run_single_test(test_case, db) if suite else None
                total += 1
                if result and result.passed:
                    passed += 1
            except Exception as e:
                total += 1
                logger.debug(f"Test failed: {e}")

        execution_time = time.time() - start_time

        # Calculate metrics
        accuracy = passed / total if total > 0 else 0.0
        precision = accuracy  # Simplified
        recall = accuracy
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Store result
        benchmark_model = BenchmarkResultModel(
            component=component,
            version="1.0",
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            execution_time=execution_time,
            sample_size=total
        )
        db.add(benchmark_model)
        db.commit()
        db.refresh(benchmark_model)

        logger.info(
            f"Benchmark {component}: accuracy={accuracy:.1%}, "
            f"time={execution_time:.2f}s, samples={total}"
        )

        return BenchmarkResult(
            id=benchmark_model.id,
            component=component,
            version="1.0",
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            execution_time=execution_time,
            sample_size=total,
            timestamp=benchmark_model.timestamp
        )

    def _get_suite(self, component: str):
        """Get test suite for component."""
        try:
            if component == "linking":
                from .test_suites.linking_tests import LinkingTestSuite
                return LinkingTestSuite()
            elif component == "extraction":
                from .test_suites.extraction_tests import ExtractionTestSuite
                return ExtractionTestSuite()
            elif component == "prediction":
                from .test_suites.prediction_tests import PredictionTestSuite
                return PredictionTestSuite()
            elif component == "runtime":
                from .test_suites.runtime_tests import RuntimeTestSuite
                return RuntimeTestSuite()
            elif component == "pdp":
                from .test_suites.pdp_tests import PDPTestSuite
                return PDPTestSuite()
        except ImportError as e:
            logger.warning(f"Could not load suite {component}: {e}")
        return None

    def _generate_synthetic_tests(
        self,
        component: str,
        count: int
    ) -> List[Dict]:
        """Generate synthetic test cases for benchmarking."""
        tests = []
        for i in range(count):
            tests.append({
                "test_name": f"synthetic_{component}_{i}",
                "input": {"text": f"Synthetic test input {i}"},
                "expected": {"result": True}
            })
        return tests

    def benchmark_linking_speed(
        self,
        sample_size: int,
        db: Session
    ) -> float:
        """Benchmark linking speed.

        Args:
            sample_size: Number of items to link
            db: Database session

        Returns:
            Average time per item in seconds
        """
        from .test_suites.linking_tests import LinkingTestSuite

        suite = LinkingTestSuite()
        test_cases = suite.test_cases[:sample_size]

        start_time = time.time()
        for test_case in test_cases:
            suite._run_single_test(test_case, db)
        total_time = time.time() - start_time

        return total_time / len(test_cases) if test_cases else 0.0

    def benchmark_extraction_speed(
        self,
        sample_size: int,
        db: Session
    ) -> float:
        """Benchmark extraction speed.

        Args:
            sample_size: Number of documents to extract from
            db: Database session

        Returns:
            Average time per document in seconds
        """
        from .test_suites.extraction_tests import ExtractionTestSuite

        suite = ExtractionTestSuite()
        test_cases = suite.test_cases[:sample_size]

        start_time = time.time()
        for test_case in test_cases:
            suite._run_single_test(test_case, db)
        total_time = time.time() - start_time

        return total_time / len(test_cases) if test_cases else 0.0

    def benchmark_runtime_execution(
        self,
        sample_size: int,
        db: Session
    ) -> float:
        """Benchmark runtime execution speed.

        Args:
            sample_size: Number of queries to execute
            db: Database session

        Returns:
            Average time per query in seconds
        """
        from .test_suites.runtime_tests import RuntimeTestSuite

        suite = RuntimeTestSuite()
        test_cases = suite.test_cases[:sample_size]

        start_time = time.time()
        for test_case in test_cases:
            suite._run_single_test(test_case, db)
        total_time = time.time() - start_time

        return total_time / len(test_cases) if test_cases else 0.0

    def compare_versions(
        self,
        component: str,
        v1: str,
        v2: str,
        db: Session
    ) -> Dict:
        """Compare benchmark results between two versions.

        Args:
            component: Component to compare
            v1: First version
            v2: Second version
            db: Database session

        Returns:
            Comparison results
        """
        result_v1 = db.query(BenchmarkResultModel).filter(
            BenchmarkResultModel.component == component,
            BenchmarkResultModel.version == v1
        ).order_by(BenchmarkResultModel.timestamp.desc()).first()

        result_v2 = db.query(BenchmarkResultModel).filter(
            BenchmarkResultModel.component == component,
            BenchmarkResultModel.version == v2
        ).order_by(BenchmarkResultModel.timestamp.desc()).first()

        if not result_v1 or not result_v2:
            return {"error": "Results not found for specified versions"}

        return {
            "component": component,
            "v1": {
                "version": v1,
                "accuracy": result_v1.accuracy,
                "execution_time": result_v1.execution_time
            },
            "v2": {
                "version": v2,
                "accuracy": result_v2.accuracy,
                "execution_time": result_v2.execution_time
            },
            "accuracy_change": (result_v2.accuracy or 0) - (result_v1.accuracy or 0),
            "speed_change": (
                (result_v1.execution_time or 1) - (result_v2.execution_time or 1)
            ) / (result_v1.execution_time or 1) * 100,
            "improved": (result_v2.accuracy or 0) > (result_v1.accuracy or 0)
        }

    def get_benchmark_history(
        self,
        component: str,
        limit: int,
        db: Session
    ) -> List[BenchmarkResult]:
        """Get benchmark history for a component.

        Args:
            component: Component name
            limit: Maximum results
            db: Database session

        Returns:
            List of historical benchmark results
        """
        results = db.query(BenchmarkResultModel).filter(
            BenchmarkResultModel.component == component
        ).order_by(
            BenchmarkResultModel.timestamp.desc()
        ).limit(limit).all()

        return [
            BenchmarkResult(
                id=r.id,
                component=r.component,
                version=r.version,
                accuracy=r.accuracy,
                precision=r.precision,
                recall=r.recall,
                f1_score=r.f1_score,
                execution_time=r.execution_time,
                sample_size=r.sample_size,
                timestamp=r.timestamp
            )
            for r in results
        ]
