"""Pydantic schemas for Evaluation Harness."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TestSuiteType(str, Enum):
    """Test suite types."""
    LINKING = "linking"
    EXTRACTION = "extraction"
    PREDICTION = "prediction"
    RUNTIME = "runtime"
    PDP = "pdp"


class TestStatus(str, Enum):
    """Test run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MetricType(str, Enum):
    """Metric types."""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"


class MetricStatus(str, Enum):
    """Metric status."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class DataType(str, Enum):
    """Ground truth data types."""
    BOQ_SPEC_LINK = "boq_spec_link"
    CONTRACT_CLAUSE = "contract_clause"
    SCHEDULE_DELAY = "schedule_delay"


class AlertType(str, Enum):
    """Alert types."""
    ACCURACY_DROP = "accuracy_drop"
    THRESHOLD_BREACH = "threshold_breach"
    TEST_FAILURE = "test_failure"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# Request/Response schemas

class TestCaseBase(BaseModel):
    """Base test case schema."""
    test_suite: TestSuiteType
    test_name: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class TestCaseCreate(TestCaseBase):
    """Create test case schema."""
    pass


class TestCase(TestCaseBase):
    """Test case response schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    active: bool

    class Config:
        from_attributes = True


class TestRunBase(BaseModel):
    """Base test run schema."""
    test_suite: TestSuiteType
    status: TestStatus = TestStatus.PENDING


class TestRunCreate(TestRunBase):
    """Create test run schema."""
    config: Optional[Dict[str, Any]] = None


class TestRun(BaseModel):
    """Test run response schema."""
    id: int
    test_suite: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    total_tests: int
    passed_tests: int
    failed_tests: int = 0
    accuracy_score: Optional[float] = None
    config_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class TestResultBase(BaseModel):
    """Base test result schema."""
    test_name: str
    passed: bool
    actual_output: Optional[Dict[str, Any]] = None
    expected_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None


class TestResult(TestResultBase):
    """Test result response schema."""
    id: int
    test_run_id: int
    test_case_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationMetricBase(BaseModel):
    """Base evaluation metric schema."""
    metric_name: str
    metric_type: MetricType
    value: float
    threshold: Optional[float] = None
    status: Optional[MetricStatus] = None


class EvaluationMetric(EvaluationMetricBase):
    """Evaluation metric response schema."""
    id: Optional[int] = None
    project_id: Optional[int] = None
    test_run_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class GroundTruthBase(BaseModel):
    """Base ground truth schema."""
    data_type: DataType
    source_text: str
    expected_entities: Optional[Dict[str, Any]] = None
    expected_links: Optional[List[Dict[str, Any]]] = None


class GroundTruthCreate(GroundTruthBase):
    """Create ground truth schema."""
    project_id: Optional[int] = None


class GroundTruth(GroundTruthBase):
    """Ground truth response schema."""
    id: int
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    project_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BenchmarkResultBase(BaseModel):
    """Base benchmark result schema."""
    component: str
    version: Optional[str] = None
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    execution_time: Optional[float] = None
    sample_size: Optional[int] = None


class BenchmarkResult(BenchmarkResultBase):
    """Benchmark result response schema."""
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class AlertBase(BaseModel):
    """Base alert schema."""
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None


class Alert(AlertBase):
    """Alert response schema."""
    id: int
    test_run_id: Optional[int] = None
    acknowledged: bool
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationReport(BaseModel):
    """Evaluation report schema."""
    test_run_id: int
    test_suite: str
    summary: Dict[str, Any]
    metrics: List[EvaluationMetric]
    failed_tests: List[TestResult]
    recommendations: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class TestSuiteConfig(BaseModel):
    """Test suite configuration schema."""
    suite_name: TestSuiteType
    enabled: bool = True
    threshold: float
    alert_on_failure: bool = True
    schedule_cron: Optional[str] = None


class RunSuiteRequest(BaseModel):
    """Request to run a test suite."""
    config: Optional[Dict[str, Any]] = None


class BenchmarkRequest(BaseModel):
    """Request to run benchmarks."""
    components: List[str]
    sample_size: int = 100
