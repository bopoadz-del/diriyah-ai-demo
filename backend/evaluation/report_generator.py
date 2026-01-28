"""Report Generator - Generate evaluation reports."""

import base64
import io
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .models import TestRun as TestRunModel, TestResult as TestResultModel, EvaluationMetric
from .schemas import EvaluationReport, TestResult
from .test_harness import THRESHOLDS, TEST_SUITES

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate evaluation reports in various formats."""

    def generate_summary_report(
        self,
        test_run_id: int,
        db: Session
    ) -> str:
        """Generate a markdown summary report.

        Args:
            test_run_id: ID of the test run
            db: Database session

        Returns:
            Markdown formatted report
        """
        test_run = db.query(TestRunModel).filter(
            TestRunModel.id == test_run_id
        ).first()

        if not test_run:
            return "# Error\n\nTest run not found."

        results = db.query(TestResultModel).filter(
            TestResultModel.test_run_id == test_run_id
        ).all()

        failed_results = [r for r in results if not r.passed]
        threshold = THRESHOLDS.get(test_run.test_suite, 0.90)
        meets_threshold = (test_run.accuracy_score or 0) >= threshold

        # Build markdown report
        lines = [
            f"# Evaluation Report: {TEST_SUITES.get(test_run.test_suite, test_run.test_suite)}",
            "",
            f"**Run ID:** {test_run_id}",
            f"**Suite:** {test_run.test_suite}",
            f"**Status:** {test_run.status}",
            f"**Date:** {test_run.started_at.strftime('%Y-%m-%d %H:%M:%S') if test_run.started_at else 'N/A'}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Tests | {test_run.total_tests} |",
            f"| Passed | {test_run.passed_tests} |",
            f"| Failed | {test_run.failed_tests} |",
            f"| Accuracy | {test_run.accuracy_score:.1%} |" if test_run.accuracy_score else "| Accuracy | N/A |",
            f"| Threshold | {threshold:.1%} |",
            f"| Status | {'PASS' if meets_threshold else 'FAIL'} |",
            "",
        ]

        if failed_results:
            lines.extend([
                "## Failed Tests",
                "",
            ])
            for result in failed_results[:10]:  # Limit to first 10
                lines.append(f"- **{result.test_name}**: {result.error_message or 'No details'}")
            if len(failed_results) > 10:
                lines.append(f"- ... and {len(failed_results) - 10} more")
            lines.append("")

        lines.extend([
            "## Recommendations",
            "",
        ])

        if not meets_threshold:
            gap = threshold - (test_run.accuracy_score or 0)
            lines.append(f"- Accuracy is {gap:.1%} below threshold. Review failed tests.")
        if test_run.failed_tests > 5:
            lines.append("- High failure rate. Consider reviewing test cases or implementation.")
        if meets_threshold:
            lines.append("- All thresholds met. Consider adding more edge case tests.")

        lines.extend([
            "",
            "---",
            f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
        ])

        return "\n".join(lines)

    def generate_detailed_report(
        self,
        test_run_id: int,
        db: Session
    ) -> str:
        """Generate an HTML detailed report.

        Args:
            test_run_id: ID of the test run
            db: Database session

        Returns:
            HTML formatted report
        """
        test_run = db.query(TestRunModel).filter(
            TestRunModel.id == test_run_id
        ).first()

        if not test_run:
            return "<html><body><h1>Error</h1><p>Test run not found.</p></body></html>"

        results = db.query(TestResultModel).filter(
            TestResultModel.test_run_id == test_run_id
        ).all()

        failed_results = [r for r in results if not r.passed]
        threshold = THRESHOLDS.get(test_run.test_suite, 0.90)
        meets_threshold = (test_run.accuracy_score or 0) >= threshold
        status_color = "#28a745" if meets_threshold else "#dc3545"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Evaluation Report - {test_run.test_suite}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .status {{ display: inline-block; padding: 4px 12px; border-radius: 4px; color: white; font-weight: bold; }}
        .status.pass {{ background: #28a745; }}
        .status.fail {{ background: #dc3545; }}
        .metric-card {{ display: inline-block; background: #fff; border: 1px solid #dee2e6; padding: 20px; margin: 10px; border-radius: 8px; min-width: 150px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: {status_color}; }}
        .metric-label {{ color: #6c757d; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
        th {{ background: #f8f9fa; }}
        .failed {{ background: #fff3cd; }}
        .passed {{ background: #d4edda; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Evaluation Report</h1>
        <p><strong>Suite:</strong> {TEST_SUITES.get(test_run.test_suite, test_run.test_suite)}</p>
        <p><strong>Run ID:</strong> {test_run_id}</p>
        <p><strong>Date:</strong> {test_run.started_at.strftime('%Y-%m-%d %H:%M:%S') if test_run.started_at else 'N/A'}</p>
        <span class="status {'pass' if meets_threshold else 'fail'}">{'PASS' if meets_threshold else 'FAIL'}</span>
    </div>

    <h2>Metrics Summary</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{test_run.accuracy_score:.1%}</div>
            <div class="metric-label">Accuracy</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{test_run.passed_tests}</div>
            <div class="metric-label">Passed</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{test_run.failed_tests}</div>
            <div class="metric-label">Failed</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{threshold:.1%}</div>
            <div class="metric-label">Threshold</div>
        </div>
    </div>

    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Status</th>
            <th>Execution Time</th>
            <th>Error</th>
        </tr>
"""

        for result in results:
            status_class = "passed" if result.passed else "failed"
            status_text = "PASS" if result.passed else "FAIL"
            exec_time = f"{result.execution_time:.3f}s" if result.execution_time else "N/A"
            error = result.error_message or "-"

            html += f"""
        <tr class="{status_class}">
            <td>{result.test_name}</td>
            <td>{status_text}</td>
            <td>{exec_time}</td>
            <td>{error[:100]}{'...' if len(error) > 100 else ''}</td>
        </tr>
"""

        html += f"""
    </table>

    <h2>Recommendations</h2>
    <ul>
"""

        if not meets_threshold:
            gap = threshold - (test_run.accuracy_score or 0)
            html += f"        <li>Accuracy is {gap:.1%} below threshold. Review failed tests.</li>\n"
        if test_run.failed_tests > 5:
            html += "        <li>High failure rate. Review test implementation.</li>\n"
        if meets_threshold:
            html += "        <li>All thresholds met. Consider adding edge case tests.</li>\n"

        html += f"""
    </ul>

    <footer>
        <p style="color: #6c757d; margin-top: 40px;">
            Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        </p>
    </footer>
</body>
</html>
"""

        return html

    def generate_metrics_chart(
        self,
        metric_name: str,
        days: int,
        db: Session
    ) -> str:
        """Generate a base64-encoded chart image for metrics over time.

        Args:
            metric_name: Name of the metric
            days: Number of days of history
            db: Database session

        Returns:
            Base64-encoded PNG image
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
        except ImportError:
            logger.warning("matplotlib not available for chart generation")
            return ""

        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        metrics = db.query(EvaluationMetric).filter(
            EvaluationMetric.metric_name == metric_name,
            EvaluationMetric.timestamp >= cutoff
        ).order_by(EvaluationMetric.timestamp).all()

        if not metrics:
            return ""

        dates = [m.timestamp for m in metrics]
        values = [m.value * 100 for m in metrics]  # Convert to percentage
        threshold = metrics[0].threshold * 100 if metrics[0].threshold else 90

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(dates, values, 'b-', linewidth=2, marker='o', markersize=4)
        ax.axhline(y=threshold, color='r', linestyle='--', label=f'Threshold ({threshold:.0f}%)')
        ax.fill_between(dates, values, threshold, where=[v >= threshold for v in values],
                       alpha=0.3, color='green')
        ax.fill_between(dates, values, threshold, where=[v < threshold for v in values],
                       alpha=0.3, color='red')

        ax.set_xlabel('Date')
        ax.set_ylabel('Accuracy (%)')
        ax.set_title(f'{metric_name} Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()

        return image_base64

    def generate_comparison_report(
        self,
        run1_id: int,
        run2_id: int,
        db: Session
    ) -> str:
        """Generate a comparison report between two test runs.

        Args:
            run1_id: First test run ID
            run2_id: Second test run ID
            db: Database session

        Returns:
            Markdown formatted comparison
        """
        run1 = db.query(TestRunModel).filter(TestRunModel.id == run1_id).first()
        run2 = db.query(TestRunModel).filter(TestRunModel.id == run2_id).first()

        if not run1 or not run2:
            return "# Error\n\nOne or both test runs not found."

        acc1 = run1.accuracy_score or 0
        acc2 = run2.accuracy_score or 0
        change = acc2 - acc1
        improved = change > 0

        lines = [
            "# Test Run Comparison",
            "",
            f"Comparing Run #{run1_id} vs Run #{run2_id}",
            "",
            "## Summary",
            "",
            "| Metric | Run #{} | Run #{} | Change |".format(run1_id, run2_id),
            "|--------|---------|---------|--------|",
            "| Accuracy | {:.1%} | {:.1%} | {:+.1%} {} |".format(
                acc1, acc2, change, "" if improved else ""
            ),
            "| Passed | {} | {} | {:+d} |".format(
                run1.passed_tests, run2.passed_tests,
                run2.passed_tests - run1.passed_tests
            ),
            "| Failed | {} | {} | {:+d} |".format(
                run1.failed_tests, run2.failed_tests,
                run2.failed_tests - run1.failed_tests
            ),
            "",
            "## Verdict",
            "",
            f"**{'Improved' if improved else 'Regression'}** - Accuracy {'increased' if improved else 'decreased'} by {abs(change):.1%}",
            "",
            "---",
            f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
        ]

        return "\n".join(lines)

    def export_report_pdf(
        self,
        test_run_id: int,
        db: Session
    ) -> bytes:
        """Export report as PDF.

        Args:
            test_run_id: ID of the test run
            db: Database session

        Returns:
            PDF content as bytes
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
        except ImportError:
            logger.warning("reportlab not available for PDF generation")
            # Return a simple error message as PDF placeholder
            return b"PDF generation requires reportlab library."

        test_run = db.query(TestRunModel).filter(
            TestRunModel.id == test_run_id
        ).first()

        if not test_run:
            return b"Test run not found."

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(
            f"Evaluation Report - {test_run.test_suite}",
            styles['Heading1']
        ))
        elements.append(Spacer(1, 12))

        # Summary
        elements.append(Paragraph("Summary", styles['Heading2']))
        threshold = THRESHOLDS.get(test_run.test_suite, 0.90)

        summary_data = [
            ["Metric", "Value"],
            ["Run ID", str(test_run_id)],
            ["Suite", test_run.test_suite],
            ["Total Tests", str(test_run.total_tests)],
            ["Passed", str(test_run.passed_tests)],
            ["Failed", str(test_run.failed_tests)],
            ["Accuracy", f"{test_run.accuracy_score:.1%}" if test_run.accuracy_score else "N/A"],
            ["Threshold", f"{threshold:.1%}"],
            ["Status", "PASS" if (test_run.accuracy_score or 0) >= threshold else "FAIL"]
        ]

        table = Table(summary_data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(table)
        elements.append(Spacer(1, 24))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        return buffer.read()
