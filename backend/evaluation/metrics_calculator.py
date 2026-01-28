"""Metrics Calculator for evaluation results."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .schemas import TestResult as TestResultSchema


@dataclass
class ConfusionMatrix:
    """Confusion matrix data."""
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0


class MetricsCalculator:
    """Calculate evaluation metrics from test results."""

    @staticmethod
    def calculate_accuracy(results: List[TestResultSchema]) -> float:
        """Calculate accuracy: (TP + TN) / (TP + TN + FP + FN).

        For simple pass/fail tests, this is passed_count / total_count.
        """
        if not results:
            return 0.0

        passed = sum(1 for r in results if r.passed)
        return passed / len(results)

    @staticmethod
    def calculate_precision(
        true_positives: int,
        false_positives: int
    ) -> float:
        """Calculate precision: TP / (TP + FP)."""
        denominator = true_positives + false_positives
        if denominator == 0:
            return 0.0
        return true_positives / denominator

    @staticmethod
    def calculate_recall(
        true_positives: int,
        false_negatives: int
    ) -> float:
        """Calculate recall: TP / (TP + FN)."""
        denominator = true_positives + false_negatives
        if denominator == 0:
            return 0.0
        return true_positives / denominator

    @staticmethod
    def calculate_f1_score(precision: float, recall: float) -> float:
        """Calculate F1 score: 2 * (P * R) / (P + R)."""
        denominator = precision + recall
        if denominator == 0:
            return 0.0
        return 2 * (precision * recall) / denominator

    @classmethod
    def calculate_all_metrics(
        cls,
        results: List[TestResultSchema],
        confusion_matrix: Optional[ConfusionMatrix] = None
    ) -> Dict[str, float]:
        """Calculate all metrics from results.

        Args:
            results: List of test results
            confusion_matrix: Optional pre-calculated confusion matrix

        Returns:
            Dictionary with accuracy, precision, recall, and f1 scores
        """
        accuracy = cls.calculate_accuracy(results)

        if confusion_matrix:
            precision = cls.calculate_precision(
                confusion_matrix.true_positives,
                confusion_matrix.false_positives
            )
            recall = cls.calculate_recall(
                confusion_matrix.true_positives,
                confusion_matrix.false_negatives
            )
        else:
            # Default to accuracy-based metrics for simple pass/fail
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed
            precision = passed / (passed + failed) if (passed + failed) > 0 else 0.0
            recall = 1.0 if failed == 0 else passed / len(results)

        f1 = cls.calculate_f1_score(precision, recall)

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    @classmethod
    def calculate_confusion_matrix(
        cls,
        results: List[TestResultSchema],
        get_expected_and_actual: callable = None
    ) -> ConfusionMatrix:
        """Calculate confusion matrix from results.

        For linking/extraction tests:
        - TP: Correct item found
        - FP: Incorrect item found
        - FN: Expected item not found
        - TN: Correctly identified no item

        Args:
            results: Test results
            get_expected_and_actual: Optional function to extract expected/actual sets

        Returns:
            ConfusionMatrix with counts
        """
        matrix = ConfusionMatrix()

        for result in results:
            if get_expected_and_actual and result.expected_output and result.actual_output:
                expected, actual = get_expected_and_actual(
                    result.expected_output,
                    result.actual_output
                )

                # Calculate TP, FP, FN from sets
                tp = len(expected & actual)
                fp = len(actual - expected)
                fn = len(expected - actual)

                matrix.true_positives += tp
                matrix.false_positives += fp
                matrix.false_negatives += fn

                # TN is when we correctly have no match
                if not expected and not actual:
                    matrix.true_negatives += 1
            else:
                # Simple pass/fail
                if result.passed:
                    matrix.true_positives += 1
                else:
                    matrix.false_negatives += 1

        return matrix

    @classmethod
    def calculate_per_class_metrics(
        cls,
        results: List[TestResultSchema],
        class_key: str = "type"
    ) -> Dict[str, Dict[str, float]]:
        """Calculate metrics per class/category.

        Args:
            results: Test results with metadata containing class info
            class_key: Key in metadata to group by

        Returns:
            Dictionary mapping class name to metrics
        """
        # Group results by class
        grouped: Dict[str, List[TestResultSchema]] = {}

        for result in results:
            if result.expected_output and class_key in result.expected_output:
                class_name = result.expected_output[class_key]
            else:
                class_name = "unknown"

            if class_name not in grouped:
                grouped[class_name] = []
            grouped[class_name].append(result)

        # Calculate metrics per class
        per_class_metrics = {}
        for class_name, class_results in grouped.items():
            per_class_metrics[class_name] = cls.calculate_all_metrics(class_results)

        return per_class_metrics

    @staticmethod
    def calculate_mean_execution_time(results: List[TestResultSchema]) -> float:
        """Calculate mean execution time from results."""
        times = [r.execution_time for r in results if r.execution_time is not None]
        if not times:
            return 0.0
        return sum(times) / len(times)

    @staticmethod
    def calculate_tolerance_accuracy(
        results: List[TestResultSchema],
        tolerance_key: str = "tolerance"
    ) -> Tuple[float, int, int]:
        """Calculate accuracy with tolerance for numeric predictions.

        Args:
            results: Test results with expected/actual numeric values
            tolerance_key: Key for tolerance in expected_output

        Returns:
            Tuple of (accuracy, within_tolerance_count, total_count)
        """
        within_tolerance = 0
        total = 0

        for result in results:
            if not result.expected_output or not result.actual_output:
                continue

            expected_value = result.expected_output.get("value")
            actual_value = result.actual_output.get("value")
            tolerance = result.expected_output.get(tolerance_key, 0)

            if expected_value is not None and actual_value is not None:
                total += 1
                if abs(expected_value - actual_value) <= tolerance:
                    within_tolerance += 1

        accuracy = within_tolerance / total if total > 0 else 0.0
        return accuracy, within_tolerance, total
