"""Context builder for assembling project data for code execution."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Keywords that trigger specific data fetching
DATA_KEYWORDS: Dict[str, Set[str]] = {
    "boq": {"boq", "quantity", "quantities", "material", "materials", "item", "items"},
    "schedule": {"schedule", "task", "tasks", "delay", "duration", "milestone", "timeline"},
    "cost": {"cost", "costs", "budget", "variance", "expense", "spending", "price", "prices"},
    "payment": {"payment", "invoice", "certification", "ipc", "billing"},
    "variation": {"variation", "change", "vo", "change order"},
}


class ContextBuilder:
    """Builds execution context by fetching relevant project data."""

    def __init__(self, db_session=None):
        """Initialize the context builder.

        Args:
            db_session: Optional database session for fetching data.
        """
        self._db = db_session

    def build_context(
        self,
        project_id: Optional[int],
        query: str,
        db=None,
    ) -> Dict[str, Any]:
        """Build execution context based on query and project.

        Args:
            project_id: Project ID to fetch data for.
            query: User query to analyze for required data.
            db: Database session (overrides constructor session).

        Returns:
            Dictionary of context data for code execution.
        """
        db = db or self._db
        context: Dict[str, Any] = {}

        # Detect what data is needed
        required_data = self._detect_required_data(query)
        logger.info("Required data types for query: %s", required_data)

        # Fetch project data if project_id provided
        if project_id and db:
            if "boq" in required_data:
                context["boq_items"] = self._fetch_boq_data(project_id, db)

            if "schedule" in required_data:
                context["tasks"] = self._fetch_schedule_data(project_id, db)

            if "cost" in required_data:
                context["cost_data"] = self._fetch_cost_data(project_id, db)

            if "payment" in required_data:
                context["payments"] = self._fetch_payment_data(project_id, db)

            if "variation" in required_data:
                context["variations"] = self._fetch_variation_data(project_id, db)

        # Add utility context
        context["project_id"] = project_id

        # Add sample/mock data if no real data available
        if not context.get("boq_items") and "boq" in required_data:
            context["boq_items"] = self._get_sample_boq_data()

        if not context.get("tasks") and "schedule" in required_data:
            context["tasks"] = self._get_sample_schedule_data()

        if not context.get("cost_data") and "cost" in required_data:
            context["cost_data"] = self._get_sample_cost_data()

        return context

    def _detect_required_data(self, query: str) -> List[str]:
        """Detect what data types are needed based on query.

        Args:
            query: User query to analyze.

        Returns:
            List of required data types.
        """
        query_lower = query.lower()
        required = []

        for data_type, keywords in DATA_KEYWORDS.items():
            if any(keyword in query_lower for keyword in keywords):
                required.append(data_type)

        # Default to BOQ and cost if nothing detected
        if not required:
            required = ["boq", "cost"]

        return required

    def _fetch_boq_data(self, project_id: int, db) -> List[Dict[str, Any]]:
        """Fetch BOQ items for project.

        Args:
            project_id: Project ID.
            db: Database session.

        Returns:
            List of BOQ item dictionaries.
        """
        try:
            # Try to query from database
            from sqlalchemy import text

            result = db.execute(
                text("""
                    SELECT id, description, quantity, unit, unit_cost
                    FROM boq_items
                    WHERE project_id = :project_id
                """),
                {"project_id": project_id},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "description": row[1],
                    "quantity": float(row[2]) if row[2] else 0,
                    "unit": row[3],
                    "unit_cost": float(row[4]) if row[4] else 0,
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("Could not fetch BOQ data: %s", e)
            return self._get_sample_boq_data()

    def _fetch_schedule_data(self, project_id: int, db) -> List[Dict[str, Any]]:
        """Fetch schedule tasks for project.

        Args:
            project_id: Project ID.
            db: Database session.

        Returns:
            List of task dictionaries.
        """
        try:
            from sqlalchemy import text

            result = db.execute(
                text("""
                    SELECT id, name, planned_start, planned_end,
                           actual_start, actual_end, progress
                    FROM tasks
                    WHERE project_id = :project_id
                """),
                {"project_id": project_id},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "planned_start": row[2],
                    "planned_end": row[3],
                    "actual_start": row[4],
                    "actual_end": row[5],
                    "progress": float(row[6]) if row[6] else 0,
                    "planned_value": 100,  # Default
                    "earned_value": float(row[6]) if row[6] else 0,
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("Could not fetch schedule data: %s", e)
            return self._get_sample_schedule_data()

    def _fetch_cost_data(self, project_id: int, db) -> Dict[str, Any]:
        """Fetch cost data for project.

        Args:
            project_id: Project ID.
            db: Database session.

        Returns:
            Cost data dictionary.
        """
        try:
            from sqlalchemy import text

            result = db.execute(
                text("""
                    SELECT budget, actual_cost, forecast
                    FROM project_costs
                    WHERE project_id = :project_id
                """),
                {"project_id": project_id},
            )
            row = result.fetchone()
            if row:
                return {
                    "budget": float(row[0]) if row[0] else 0,
                    "actual": float(row[1]) if row[1] else 0,
                    "forecast": float(row[2]) if row[2] else None,
                }
        except Exception as e:
            logger.warning("Could not fetch cost data: %s", e)

        return self._get_sample_cost_data()

    def _fetch_payment_data(self, project_id: int, db) -> List[Dict[str, Any]]:
        """Fetch payment data for project."""
        try:
            from sqlalchemy import text

            result = db.execute(
                text("""
                    SELECT id, certificate_no, amount, date, status
                    FROM payments
                    WHERE project_id = :project_id
                """),
                {"project_id": project_id},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "certificate_no": row[1],
                    "amount": float(row[2]) if row[2] else 0,
                    "date": row[3],
                    "status": row[4],
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("Could not fetch payment data: %s", e)
            return []

    def _fetch_variation_data(self, project_id: int, db) -> List[Dict[str, Any]]:
        """Fetch variation orders for project."""
        try:
            from sqlalchemy import text

            result = db.execute(
                text("""
                    SELECT id, vo_number, description, amount, status
                    FROM variations
                    WHERE project_id = :project_id
                """),
                {"project_id": project_id},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "vo_number": row[1],
                    "description": row[2],
                    "amount": float(row[3]) if row[3] else 0,
                    "status": row[4],
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("Could not fetch variation data: %s", e)
            return []

    def _get_sample_boq_data(self) -> List[Dict[str, Any]]:
        """Get sample BOQ data for testing/demo."""
        return [
            {"id": 1, "description": "Concrete Grade C40", "quantity": 500, "unit": "m3", "unit_cost": 150},
            {"id": 2, "description": "Steel Reinforcement", "quantity": 50, "unit": "ton", "unit_cost": 2500},
            {"id": 3, "description": "Formwork", "quantity": 1000, "unit": "sqm", "unit_cost": 45},
            {"id": 4, "description": "Excavation", "quantity": 2000, "unit": "m3", "unit_cost": 25},
            {"id": 5, "description": "Waterproofing Membrane", "quantity": 800, "unit": "sqm", "unit_cost": 35},
        ]

    def _get_sample_schedule_data(self) -> List[Dict[str, Any]]:
        """Get sample schedule data for testing/demo."""
        return [
            {"id": 1, "name": "Foundation", "planned_value": 100000, "earned_value": 95000, "planned_duration": 30, "actual_duration": 32},
            {"id": 2, "name": "Structure", "planned_value": 200000, "earned_value": 180000, "planned_duration": 60, "actual_duration": 65},
            {"id": 3, "name": "MEP Rough-in", "planned_value": 80000, "earned_value": 70000, "planned_duration": 40, "actual_duration": 42},
            {"id": 4, "name": "Finishes", "planned_value": 120000, "earned_value": 60000, "planned_duration": 45, "actual_duration": 25},
        ]

    def _get_sample_cost_data(self) -> Dict[str, Any]:
        """Get sample cost data for testing/demo."""
        return {
            "budget": 1000000,
            "actual": 850000,
            "forecast": 1050000,
            "categories": {
                "Materials": 400000,
                "Labor": 300000,
                "Equipment": 100000,
                "Overhead": 50000,
            },
        }
