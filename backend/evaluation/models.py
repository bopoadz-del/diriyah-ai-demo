"""SQLAlchemy models for Evaluation Harness."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship

from backend.backend.db import Base


class TestCase(Base):
    """Test case definition for evaluation."""
    __tablename__ = "eval_test_cases"

    id = Column(Integer, primary_key=True, index=True)
    test_suite = Column(String, nullable=False, index=True)  # linking, extraction, prediction, runtime, pdp
    test_name = Column(String, nullable=False)
    input_data_json = Column(JSON, nullable=False)
    expected_output_json = Column(JSON, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)

    results = relationship("TestResult", back_populates="test_case")


class TestRun(Base):
    """A single execution of a test suite."""
    __tablename__ = "eval_test_runs"

    id = Column(Integer, primary_key=True, index=True)
    test_suite = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    accuracy_score = Column(Float, nullable=True)
    config_json = Column(JSON, nullable=True)

    results = relationship("TestResult", back_populates="test_run")
    metrics = relationship("EvaluationMetric", back_populates="test_run")


class TestResult(Base):
    """Individual test result within a test run."""
    __tablename__ = "eval_test_results"

    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, ForeignKey("eval_test_runs.id"), nullable=False)
    test_case_id = Column(Integer, ForeignKey("eval_test_cases.id"), nullable=True)
    test_name = Column(String, nullable=False)
    passed = Column(Boolean, nullable=False)
    actual_output_json = Column(JSON, nullable=True)
    expected_output_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time = Column(Float, nullable=True)  # seconds
    created_at = Column(DateTime, default=datetime.utcnow)

    test_run = relationship("TestRun", back_populates="results")
    test_case = relationship("TestCase", back_populates="results")


class EvaluationMetric(Base):
    """Evaluation metrics tracked over time."""
    __tablename__ = "eval_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_type = Column(String, nullable=False)  # accuracy, precision, recall, f1
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=True)
    status = Column(String, nullable=True)  # pass, warn, fail
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    test_run_id = Column(Integer, ForeignKey("eval_test_runs.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    test_run = relationship("TestRun", back_populates="metrics")


class GroundTruthData(Base):
    """Verified ground truth data for testing."""
    __tablename__ = "eval_ground_truth"

    id = Column(Integer, primary_key=True, index=True)
    data_type = Column(String, nullable=False, index=True)  # boq_spec_link, contract_clause, schedule_delay
    source_text = Column(Text, nullable=False)
    expected_entities_json = Column(JSON, nullable=True)
    expected_links_json = Column(JSON, nullable=True)
    verified_by = Column(Integer, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BenchmarkResult(Base):
    """Performance benchmark results."""
    __tablename__ = "eval_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    component = Column(String, nullable=False, index=True)
    version = Column(String, nullable=True)
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    execution_time = Column(Float, nullable=True)  # seconds
    sample_size = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class EvaluationAlert(Base):
    """Alerts when metrics fall below thresholds."""
    __tablename__ = "eval_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, nullable=False)  # accuracy_drop, threshold_breach, test_failure
    severity = Column(String, nullable=False)  # critical, warning, info
    message = Column(Text, nullable=False)
    metric_name = Column(String, nullable=True)
    current_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    test_run_id = Column(Integer, ForeignKey("eval_test_runs.id"), nullable=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
