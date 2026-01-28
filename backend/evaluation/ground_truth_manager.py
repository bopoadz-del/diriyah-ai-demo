"""Ground Truth Manager - Manage verified test data."""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .models import GroundTruthData
from .schemas import GroundTruth, GroundTruthCreate

logger = logging.getLogger(__name__)


class GroundTruthManager:
    """Manage ground truth datasets for evaluation testing."""

    def add_ground_truth(
        self,
        data: GroundTruthCreate,
        db: Session
    ) -> GroundTruth:
        """Add a ground truth entry.

        Args:
            data: Ground truth data to add
            db: Database session

        Returns:
            Created GroundTruth entry
        """
        gt_model = GroundTruthData(
            data_type=data.data_type.value,
            source_text=data.source_text,
            expected_entities_json=data.expected_entities,
            expected_links_json=data.expected_links,
            project_id=data.project_id
        )
        db.add(gt_model)
        db.commit()
        db.refresh(gt_model)

        logger.info(f"Added ground truth entry {gt_model.id} for type {data.data_type}")

        return GroundTruth(
            id=gt_model.id,
            data_type=gt_model.data_type,
            source_text=gt_model.source_text,
            expected_entities=gt_model.expected_entities_json,
            expected_links=gt_model.expected_links_json,
            verified_by=gt_model.verified_by,
            verified_at=gt_model.verified_at,
            project_id=gt_model.project_id,
            created_at=gt_model.created_at
        )

    def get_ground_truth(
        self,
        data_type: Optional[str] = None,
        verified_only: bool = False,
        project_id: Optional[int] = None,
        db: Session = None
    ) -> List[GroundTruth]:
        """Get ground truth entries.

        Args:
            data_type: Filter by data type
            verified_only: Only return verified entries
            project_id: Filter by project
            db: Database session

        Returns:
            List of GroundTruth entries
        """
        query = db.query(GroundTruthData)

        if data_type:
            query = query.filter(GroundTruthData.data_type == data_type)

        if verified_only:
            query = query.filter(GroundTruthData.verified_by.isnot(None))

        if project_id:
            query = query.filter(GroundTruthData.project_id == project_id)

        results = query.all()

        return [
            GroundTruth(
                id=r.id,
                data_type=r.data_type,
                source_text=r.source_text,
                expected_entities=r.expected_entities_json,
                expected_links=r.expected_links_json,
                verified_by=r.verified_by,
                verified_at=r.verified_at,
                project_id=r.project_id,
                created_at=r.created_at
            )
            for r in results
        ]

    def verify_ground_truth(
        self,
        gt_id: int,
        verified_by: int,
        db: Session
    ) -> bool:
        """Mark a ground truth entry as verified.

        Args:
            gt_id: Ground truth entry ID
            verified_by: User ID who verified
            db: Database session

        Returns:
            True if verification succeeded
        """
        gt = db.query(GroundTruthData).filter(
            GroundTruthData.id == gt_id
        ).first()

        if not gt:
            logger.warning(f"Ground truth {gt_id} not found")
            return False

        gt.verified_by = verified_by
        gt.verified_at = datetime.utcnow()
        db.commit()

        logger.info(f"Verified ground truth {gt_id} by user {verified_by}")
        return True

    def import_ground_truth_csv(
        self,
        csv_content: str,
        db: Session
    ) -> int:
        """Import ground truth data from CSV content.

        CSV format:
        data_type,source_text,expected_entities,expected_links,verified

        Args:
            csv_content: CSV content as string
            db: Database session

        Returns:
            Number of entries imported
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        count = 0

        for row in reader:
            try:
                data_type = row.get("data_type", "")
                source_text = row.get("source_text", "")

                if not data_type or not source_text:
                    continue

                expected_entities = None
                expected_links = None

                if row.get("expected_entities"):
                    expected_entities = json.loads(row["expected_entities"])

                if row.get("expected_links"):
                    expected_links = json.loads(row["expected_links"])

                gt = GroundTruthData(
                    data_type=data_type,
                    source_text=source_text,
                    expected_entities_json=expected_entities,
                    expected_links_json=expected_links
                )

                if row.get("verified", "").lower() == "true":
                    gt.verified_by = 0  # System verified
                    gt.verified_at = datetime.utcnow()

                db.add(gt)
                count += 1

            except Exception as e:
                logger.warning(f"Failed to import row: {e}")
                continue

        db.commit()
        logger.info(f"Imported {count} ground truth entries from CSV")

        return count

    def export_ground_truth_csv(
        self,
        data_type: Optional[str] = None,
        db: Session = None
    ) -> str:
        """Export ground truth data to CSV.

        Args:
            data_type: Filter by data type
            db: Database session

        Returns:
            CSV content as string
        """
        entries = self.get_ground_truth(data_type=data_type, db=db)

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "id", "data_type", "source_text",
                "expected_entities", "expected_links",
                "verified", "verified_by", "created_at"
            ]
        )

        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "id": entry.id,
                "data_type": entry.data_type,
                "source_text": entry.source_text,
                "expected_entities": json.dumps(entry.expected_entities) if entry.expected_entities else "",
                "expected_links": json.dumps(entry.expected_links) if entry.expected_links else "",
                "verified": entry.verified_by is not None,
                "verified_by": entry.verified_by or "",
                "created_at": entry.created_at.isoformat() if entry.created_at else ""
            })

        return output.getvalue()

    def delete_ground_truth(
        self,
        gt_id: int,
        db: Session
    ) -> bool:
        """Delete a ground truth entry.

        Args:
            gt_id: Ground truth entry ID
            db: Database session

        Returns:
            True if deletion succeeded
        """
        gt = db.query(GroundTruthData).filter(
            GroundTruthData.id == gt_id
        ).first()

        if not gt:
            return False

        db.delete(gt)
        db.commit()

        logger.info(f"Deleted ground truth {gt_id}")
        return True

    def update_ground_truth(
        self,
        gt_id: int,
        updates: Dict,
        db: Session
    ) -> Optional[GroundTruth]:
        """Update a ground truth entry.

        Args:
            gt_id: Ground truth entry ID
            updates: Fields to update
            db: Database session

        Returns:
            Updated GroundTruth or None if not found
        """
        gt = db.query(GroundTruthData).filter(
            GroundTruthData.id == gt_id
        ).first()

        if not gt:
            return None

        if "source_text" in updates:
            gt.source_text = updates["source_text"]
        if "expected_entities" in updates:
            gt.expected_entities_json = updates["expected_entities"]
        if "expected_links" in updates:
            gt.expected_links_json = updates["expected_links"]

        db.commit()
        db.refresh(gt)

        return GroundTruth(
            id=gt.id,
            data_type=gt.data_type,
            source_text=gt.source_text,
            expected_entities=gt.expected_entities_json,
            expected_links=gt.expected_links_json,
            verified_by=gt.verified_by,
            verified_at=gt.verified_at,
            project_id=gt.project_id,
            created_at=gt.created_at
        )
