"""FastAPI router for Evaluation Harness endpoints."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.evaluation.test_harness import TestHarness, TEST_SUITES, THRESHOLDS
from backend.evaluation.schemas import (
    TestRun, TestResult, EvaluationMetric, GroundTruth, GroundTruthCreate,
    BenchmarkResult, Alert, EvaluationReport, RunSuiteRequest, BenchmarkRequest,
    TestSuiteType
)
from backend.evaluation.models import (
    TestRun as TestRunModel,
    TestResult as TestResultModel,
    EvaluationMetric as EvaluationMetricModel
)
from backend.evaluation.ground_truth_manager import GroundTruthManager
from backend.evaluation.alert_manager import AlertManager
from backend.evaluation.benchmark_runner import BenchmarkRunner
from backend.evaluation.report_generator import ReportGenerator

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

# Initialize managers
harness = TestHarness()
ground_truth_manager = GroundTruthManager()
alert_manager = AlertManager()
benchmark_runner = BenchmarkRunner()
report_generator = ReportGenerator()


def _run_suite_task(suite_name: str, db_url: str):
    """Background task to run a test suite."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        harness.run_suite(suite_name, db)
    finally:
        db.close()


@router.get("/suites", response_model=dict)
async def get_available_suites():
    """Get list of available test suites and their thresholds."""
    return {
        "suites": TEST_SUITES,
        "thresholds": THRESHOLDS
    }


@router.post("/run/{suite_name}", response_model=TestRun)
async def run_test_suite(
    suite_name: str,
    request: Optional[RunSuiteRequest] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Run a specific test suite.

    Args:
        suite_name: Name of the suite (linking, extraction, prediction, runtime, pdp)
        request: Optional configuration for the run
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        TestRun with initial status
    """
    if suite_name not in TEST_SUITES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown test suite: {suite_name}. Valid suites: {list(TEST_SUITES.keys())}"
        )

    # Run synchronously for now (can be made async with background_tasks)
    try:
        result = harness.run_suite(suite_name, db, request.config if request else None)

        # Check thresholds and create alerts
        alert_manager.check_thresholds(result.id, db)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-all", response_model=List[TestRun])
async def run_all_suites(
    request: Optional[RunSuiteRequest] = None,
    db: Session = Depends(get_db)
):
    """Run all test suites.

    Args:
        request: Optional configuration for runs
        db: Database session

    Returns:
        List of TestRun results
    """
    results = harness.run_all_suites(db, request.config if request else None)

    # Check thresholds for each run
    for result in results:
        alert_manager.check_thresholds(result.id, db)

    return results


@router.get("/runs", response_model=List[TestRun])
async def get_test_runs(
    suite: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get recent test runs.

    Args:
        suite: Filter by suite name
        status: Filter by status (pending, running, completed, failed)
        limit: Maximum number of results
        offset: Number of results to skip
        db: Database session

    Returns:
        List of TestRun objects
    """
    query = db.query(TestRunModel)

    if suite:
        query = query.filter(TestRunModel.test_suite == suite)
    if status:
        query = query.filter(TestRunModel.status == status)

    query = query.order_by(TestRunModel.started_at.desc())
    query = query.offset(offset).limit(limit)

    results = query.all()

    return [TestRun.model_validate(r) for r in results]


@router.get("/runs/{run_id}", response_model=TestRun)
async def get_test_run(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get specific test run details.

    Args:
        run_id: Test run ID
        db: Database session

    Returns:
        TestRun details
    """
    test_run = db.query(TestRunModel).filter(TestRunModel.id == run_id).first()

    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")

    return TestRun.model_validate(test_run)


@router.get("/runs/{run_id}/results", response_model=List[TestResult])
async def get_test_results(
    run_id: int,
    passed_only: bool = False,
    failed_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get results for a test run.

    Args:
        run_id: Test run ID
        passed_only: Only return passed tests
        failed_only: Only return failed tests
        db: Database session

    Returns:
        List of TestResult objects
    """
    query = db.query(TestResultModel).filter(TestResultModel.test_run_id == run_id)

    if passed_only:
        query = query.filter(TestResultModel.passed == True)
    if failed_only:
        query = query.filter(TestResultModel.passed == False)

    results = query.all()

    return [
        TestResult(
            id=r.id,
            test_run_id=r.test_run_id,
            test_case_id=r.test_case_id,
            test_name=r.test_name,
            passed=r.passed,
            actual_output=r.actual_output_json,
            expected_output=r.expected_output_json,
            error_message=r.error_message,
            execution_time=r.execution_time,
            created_at=r.created_at
        )
        for r in results
    ]


@router.get("/metrics", response_model=List[EvaluationMetric])
async def get_current_metrics(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get current (latest) evaluation metrics for each suite.

    Args:
        project_id: Filter by project
        db: Database session

    Returns:
        List of latest EvaluationMetric for each metric_name
    """
    # Get the latest metric for each metric_name
    from sqlalchemy import func

    subquery = db.query(
        EvaluationMetricModel.metric_name,
        func.max(EvaluationMetricModel.timestamp).label('max_timestamp')
    ).group_by(EvaluationMetricModel.metric_name).subquery()

    query = db.query(EvaluationMetricModel).join(
        subquery,
        (EvaluationMetricModel.metric_name == subquery.c.metric_name) &
        (EvaluationMetricModel.timestamp == subquery.c.max_timestamp)
    )

    if project_id:
        query = query.filter(EvaluationMetricModel.project_id == project_id)

    results = query.all()

    return [
        EvaluationMetric(
            id=r.id,
            metric_name=r.metric_name,
            metric_type=r.metric_type,
            value=r.value,
            threshold=r.threshold,
            status=r.status,
            project_id=r.project_id,
            test_run_id=r.test_run_id,
            timestamp=r.timestamp
        )
        for r in results
    ]


@router.get("/metrics/history", response_model=List[EvaluationMetric])
async def get_metrics_history(
    metric_name: str,
    days: int = Query(default=30, le=365),
    db: Session = Depends(get_db)
):
    """Get metric history over time.

    Args:
        metric_name: Name of the metric
        days: Number of days of history
        db: Database session

    Returns:
        List of EvaluationMetric over time
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    results = db.query(EvaluationMetricModel).filter(
        EvaluationMetricModel.metric_name == metric_name,
        EvaluationMetricModel.timestamp >= cutoff
    ).order_by(EvaluationMetricModel.timestamp).all()

    return [
        EvaluationMetric(
            id=r.id,
            metric_name=r.metric_name,
            metric_type=r.metric_type,
            value=r.value,
            threshold=r.threshold,
            status=r.status,
            project_id=r.project_id,
            test_run_id=r.test_run_id,
            timestamp=r.timestamp
        )
        for r in results
    ]


@router.post("/ground-truth", response_model=GroundTruth)
async def add_ground_truth(
    data: GroundTruthCreate,
    db: Session = Depends(get_db)
):
    """Add ground truth test case.

    Args:
        data: Ground truth data to add
        db: Database session

    Returns:
        Created GroundTruth entry
    """
    return ground_truth_manager.add_ground_truth(data, db)


@router.get("/ground-truth", response_model=List[GroundTruth])
async def get_ground_truth(
    data_type: Optional[str] = None,
    verified_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get ground truth data.

    Args:
        data_type: Filter by data type
        verified_only: Only return verified entries
        db: Database session

    Returns:
        List of GroundTruth entries
    """
    return ground_truth_manager.get_ground_truth(
        data_type=data_type,
        verified_only=verified_only,
        db=db
    )


@router.put("/ground-truth/{gt_id}/verify")
async def verify_ground_truth(
    gt_id: int,
    verified_by: int = Query(...),
    db: Session = Depends(get_db)
):
    """Verify ground truth entry.

    Args:
        gt_id: Ground truth entry ID
        verified_by: User ID who verified
        db: Database session

    Returns:
        Success message
    """
    success = ground_truth_manager.verify_ground_truth(gt_id, verified_by, db)
    if not success:
        raise HTTPException(status_code=404, detail="Ground truth entry not found")
    return {"message": "Ground truth verified", "id": gt_id}


@router.get("/report/{run_id}", response_class=HTMLResponse)
async def get_evaluation_report(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get HTML evaluation report.

    Args:
        run_id: Test run ID
        db: Database session

    Returns:
        HTML report
    """
    return report_generator.generate_detailed_report(run_id, db)


@router.get("/report/{run_id}/markdown")
async def get_evaluation_report_markdown(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get markdown evaluation report.

    Args:
        run_id: Test run ID
        db: Database session

    Returns:
        Markdown report
    """
    return {"report": report_generator.generate_summary_report(run_id, db)}


@router.get("/report/{run_id}/pdf")
async def download_report_pdf(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Download PDF report.

    Args:
        run_id: Test run ID
        db: Database session

    Returns:
        PDF file response
    """
    pdf_content = report_generator.export_report_pdf(run_id, db)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=evaluation_report_{run_id}.pdf"}
    )


@router.get("/alerts", response_model=List[Alert])
async def get_alerts(
    severity: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db)
):
    """Get active evaluation alerts.

    Args:
        severity: Filter by severity (critical, warning, info)
        limit: Maximum number of alerts
        db: Database session

    Returns:
        List of active alerts
    """
    from backend.evaluation.schemas import AlertSeverity

    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity(severity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

    return alert_manager.get_active_alerts(db, severity=severity_enum, limit=limit)


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: int = Query(...),
    db: Session = Depends(get_db)
):
    """Acknowledge an alert.

    Args:
        alert_id: Alert ID to acknowledge
        acknowledged_by: User ID who acknowledged
        db: Database session

    Returns:
        Success message
    """
    success = alert_manager.acknowledge_alert(alert_id, acknowledged_by, db)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert acknowledged", "id": alert_id}


@router.post("/benchmark", response_model=List[BenchmarkResult])
async def run_benchmarks(
    request: BenchmarkRequest,
    db: Session = Depends(get_db)
):
    """Run performance benchmarks.

    Args:
        request: Benchmark configuration
        db: Database session

    Returns:
        List of benchmark results
    """
    return benchmark_runner.run_benchmarks(
        request.components,
        request.sample_size,
        db
    )


@router.get("/benchmark/history/{component}", response_model=List[BenchmarkResult])
async def get_benchmark_history(
    component: str,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """Get benchmark history for a component.

    Args:
        component: Component name
        limit: Maximum results
        db: Database session

    Returns:
        List of historical benchmark results
    """
    return benchmark_runner.get_benchmark_history(component, limit, db)


@router.get("/compare/{run1_id}/{run2_id}")
async def compare_runs(
    run1_id: int,
    run2_id: int,
    db: Session = Depends(get_db)
):
    """Compare two test runs.

    Args:
        run1_id: First test run ID
        run2_id: Second test run ID
        db: Database session

    Returns:
        Comparison results
    """
    return harness.compare_with_baseline(run1_id, run2_id, db)
