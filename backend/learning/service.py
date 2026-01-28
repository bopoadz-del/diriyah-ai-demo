"""Service helpers for feedback capture and dataset exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from backend.learning.builders import DATASET_BUILDERS, DatasetBuilder
from backend.learning.models import (
    FeedbackEvent,
    FeedbackLabel,
    FeedbackReview,
    LearningRun,
    TrainingDataset,
    TrainingDatasetRecord,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportResult:
    manifest: Dict[str, Any]
    manifest_path: Path
    records_path: Path
    dataset: TrainingDataset


def create_feedback(
    db: Session,
    workspace_id: str,
    event_type: str,
    event_payload: Optional[Dict[str, Any]],
    user_id: Optional[int] = None,
) -> FeedbackEvent:
    feedback = FeedbackEvent(
        workspace_id=workspace_id,
        user_id=user_id,
        event_type=event_type,
        event_payload=event_payload or {},
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def add_label(
    db: Session,
    feedback_id: int,
    label_type: str,
    label_value: str,
    labeled_by: Optional[int] = None,
) -> FeedbackLabel:
    label = FeedbackLabel(
        feedback_id=feedback_id,
        label_type=label_type,
        label_value=label_value,
        labeled_by=labeled_by,
    )
    db.add(label)
    db.commit()
    db.refresh(label)
    return label


def review_feedback(
    db: Session,
    feedback_id: int,
    decision: str,
    reviewer_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> FeedbackReview:
    review = FeedbackReview(
        feedback_id=feedback_id,
        decision=decision,
        reviewer_id=reviewer_id,
        notes=notes,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def export_dataset(
    db: Session,
    dataset_name: str,
    workspace_id: str,
    created_by: Optional[int] = None,
    description: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> ExportResult:
    builder = DATASET_BUILDERS.get(dataset_name)
    if builder is None:
        raise ValueError(f"Unknown dataset '{dataset_name}'")

    run = LearningRun(run_type="export", status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        dataset = _create_dataset(db, dataset_name, description, created_by)
        records, record_rows = _build_records(db, builder, workspace_id)
        for row in record_rows:
            row.dataset_id = dataset.id
        manifest, manifest_path, records_path = _write_export(
            dataset_name=dataset_name,
            version_tag=dataset.version_tag,
            workspace_id=workspace_id,
            records=records,
            output_dir=output_dir,
        )
        dataset.manifest_json = manifest
        dataset.record_count = len(records)
        run.status = "success"
        run.dataset_id = dataset.id
        run.finished_at = datetime.now(timezone.utc)
        run.details_json = {"record_count": len(records)}
        db.add_all(record_rows)
        db.commit()
        return ExportResult(
            manifest=manifest,
            manifest_path=manifest_path,
            records_path=records_path,
            dataset=dataset,
        )
    except Exception:
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.exception("Dataset export failed for %s", dataset_name)
        raise


def _create_dataset(
    db: Session,
    dataset_name: str,
    description: Optional[str],
    created_by: Optional[int],
) -> TrainingDataset:
    version_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dataset = TrainingDataset(
        name=dataset_name,
        version_tag=version_tag,
        description=description,
        created_by=created_by,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def _build_records(
    db: Session,
    builder: DatasetBuilder,
    workspace_id: str,
) -> Tuple[List[Dict[str, Any]], List[TrainingDatasetRecord]]:
    feedback_items = (
        db.query(FeedbackEvent)
        .options(joinedload(FeedbackEvent.labels), joinedload(FeedbackEvent.reviews))
        .filter(
            FeedbackEvent.workspace_id == workspace_id,
            FeedbackEvent.event_type.in_(builder.event_types),
        )
        .order_by(FeedbackEvent.id.asc())
        .all()
    )

    records: List[Dict[str, Any]] = []
    rows: List[TrainingDatasetRecord] = []

    for feedback in feedback_items:
        if not is_feedback_approved(feedback.reviews):
            continue
        label_value = _latest_label_value(feedback.labels, builder.label_type)
        record = builder.build_record(feedback, label_value)
        if record is None:
            continue
        records.append(record)
        rows.append(
            TrainingDatasetRecord(
                dataset_id=0,
                feedback_id=feedback.id,
                record_json=record,
            )
        )

    return records, rows


def _latest_label_value(labels: Iterable[FeedbackLabel], label_type: str) -> Optional[str]:
    filtered = [label for label in labels if label.label_type == label_type]
    if not filtered:
        return None
    latest = max(filtered, key=lambda label: label.id)
    return latest.label_value


def is_feedback_approved(reviews: Iterable[FeedbackReview]) -> bool:
    if not reviews:
        return False
    latest = max(reviews, key=lambda review: review.id)
    return latest.decision == "approved"


def _write_export(
    dataset_name: str,
    version_tag: str,
    workspace_id: str,
    records: List[Dict[str, Any]],
    output_dir: Optional[Path],
) -> Tuple[Dict[str, Any], Path, Path]:
    base_dir = output_dir or Path(os.getenv("LEARNING_DATASET_DIR", "backend/learning_datasets"))
    dataset_dir = base_dir / dataset_name / version_tag
    dataset_dir.mkdir(parents=True, exist_ok=True)

    records_path = dataset_dir / "records.jsonl"
    manifest_path = dataset_dir / "manifest.json"

    with records_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")

    manifest = {
        "dataset_name": dataset_name,
        "version_tag": version_tag,
        "workspace_id": workspace_id,
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records_path": str(records_path),
    }

    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    logger.info(
        "Exported dataset %s (%s records) to %s",
        dataset_name,
        len(records),
        dataset_dir,
    )

    return manifest, manifest_path, records_path
