class ReportingService:
    def __init__(self):
        self.project_status = {
            "structural": {"progress": 0.75, "approvals_pending": 3, "validation_issues": 2, "deadline": "2025-09-26"},
            "architectural": {"progress": 0.55, "approvals_pending": 5, "validation_issues": 4, "deadline": "2025-10-02"},
        }

    def generate_report(self, package: str):
        d = self.project_status.get(package.lower())
        if not d:
            return {"report": f"No data found for {package} package."}
        pct = int(d["progress"] * 100)
        return {"report": f"The {package} package is {pct}% complete. {d['approvals_pending']} approvals pending, {d['validation_issues']} validation issues. On track for {d['deadline']} deadline."}

reporting_service = ReportingService()
