"""Evaluation Harness - Automated Accuracy Testing System.

This module provides continuous validation of system accuracy:
- BOQ <-> Spec linking: Target 94% accuracy
- Contract clause extraction: Target 89% accuracy
- Delay prediction: Target 78% accuracy
- Runtime code generation: Target 85% success rate
- PDP policy decisions: Target 99% correct decisions
"""

from .test_harness import TestHarness, TEST_SUITES, THRESHOLDS
from .metrics_calculator import MetricsCalculator

__all__ = [
    "TestHarness",
    "TEST_SUITES",
    "THRESHOLDS",
    "MetricsCalculator",
]
