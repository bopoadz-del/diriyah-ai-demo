"""Dataset builders and export utilities for learning feedback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from backend.learning.models import (
    FeedbackEvent,
    FeedbackLabel,
    FeedbackReview,
    FeedbackReviewStatus,
    TrainingDataset,
    TrainingDatasetRecord,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatasetBuilder:
    name: str
    label_type: str
    build_record: Callable[[FeedbackEvent, FeedbackLabel], Optional[Dict[str, object]]]


def _build_intent_routing_record(
    feedback: FeedbackEvent,
    label: FeedbackLabel,
) -> Optional[Dict[str, object]]:
    label_data = label.label_json or {}
    expected_intent = label_data.get("intent") or label_data.get("expected_intent")
    if not expected_intent:
        return None
    return {
        "type": "intent_routing",
        "input": feedback.input_text,
        "expected_intent": expected_intent,
        "context": feedback.metadata_json or {},
    }


def _build_tool_routing_record(
    feedback: FeedbackEvent,
    label: FeedbackLabel,
) -> Optional[Dict[str, object]]:
    label_data = label.label_json or {}
    expected_tool = label_data.get("tool") or label_data.get("expected_tool")
    if not expected_tool:
        return None
    return {
        "type": "tool_routing",
        "input": feedback.input_text,
        "expected_tool": expected_tool,
        "context": feedback.metadata_json or {},
    }


def _build_ule_linking_record(
    feedback: FeedbackEvent,
    label: FeedbackLabel,
) -> Optional[Dict[str, object]]:
    label_data = label.label_json or {}
    if not label_data:
        return None
    return {
        "type": "ule_linking",
        "input": feedback.input_text,
        "link_validation": label_data,
        "context": feedback.metadata_json or {},
    }


_DATASET_BUILDERS: Dict[str, DatasetBuilder] = {
    "intent_routing": DatasetBuilder(
        name="intent_routing",
        label_type="intent_routing",
        build_record=_build_intent_routing_record,
    ),
    "tool_routing": DatasetBuilder(
        name="tool_routing",
        label_type="tool_routing",
        build_record=_build_tool_routing_record,
    ),
    "ule_linking": DatasetBuilder(
        name="ule_linking",
        label_type="ule_linking",
        build_record=_build_ule_linking_record,
    ),
}


def get_dataset_builder(dataset_name: str) -> DatasetBuilder:
    if dataset_name not in _DATASET_BUILDERS:
        raise ValueError(f"Unknown dataset builder: {dataset_name}")
    return _DATASET_BUILDERS[dataset_name]


def _latest_reviews(db: Session, feedback_ids: Iterable[int]) -> Dict[int, FeedbackReview]:
    latest: Dict[int, FeedbackReview] = {}
    if not feedback_ids:
        return latest
    reviews = (
        db.query(FeedbackReview)
        .filter(FeedbackReview.feedback_id.in_(feedback_ids))
        .order_by(FeedbackReview.feedback_id.asc(), FeedbackReview.created_at.desc())
        .all()
    )
    for review in reviews:
        if review.feedback_id not in latest:
            latest[review.feedback_id] = review
    return latest


def _latest_labels(
    db: Session,
    feedback_ids: Iterable[int],
    label_type: str,
) -> Dict[int, FeedbackLabel]:
    latest: Dict[int, FeedbackLabel] = {}
    if not feedback_ids:
        return latest
    labels = (
        db.query(FeedbackLabel)
        .filter(
            FeedbackLabel.feedback_id.in_(feedback_ids),
            FeedbackLabel.label_type == label_type,
        )
        .order_by(FeedbackLabel.feedback_id.asc(), FeedbackLabel.created_at.desc())
        .all()
    )
    for label in labels:
        if label.feedback_id not in latest:
            latest[label.feedback_id] = label
    return latest


def export_dataset(
    db: Session,
    dataset_name: str,
    workspace_id: str,
    export_dir: Path,
    max_records: Optional[int] = None,
) -> Dict[str, object]:
    builder = get_dataset_builder(dataset_name)
    version_tag = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    dataset_path = export_dir / dataset_name / version_tag
    dataset_path.mkdir(parents=True, exist_ok=True)

    feedbacks = (
        db.query(FeedbackEvent)
        .filter(FeedbackEvent.workspace_id == workspace_id)
        .order_by(FeedbackEvent.id.asc())
        .all()
    )

    feedback_ids = [feedback.id for feedback in feedbacks]
    latest_reviews = _latest_reviews(db, feedback_ids)
    latest_labels = _latest_labels(db, feedback_ids, builder.label_type)

    records: List[Dict[str, object]] = []
    records_with_feedback: List[tuple[int, Dict[str, object]]] = []
    for feedback in feedbacks:
        review = latest_reviews.get(feedback.id)
        if review is None or review.status != FeedbackReviewStatus.APPROVED:
            continue
        label = latest_labels.get(feedback.id)
        if not label:
            continue
        record = builder.build_record(feedback, label)
        if record is None:
            continue
        records.append(record)
        records_with_feedback.append((feedback.id, record))
        if max_records and len(records) >= max_records:
            break

    dataset_file = dataset_path / f"{dataset_name}.jsonl"
    with dataset_file.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "dataset_name": dataset_name,
        "workspace_id": workspace_id,
        "version_tag": version_tag,
        "record_count": len(records),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [str(dataset_file)],
    }

    manifest_file = dataset_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    dataset = TrainingDataset(
        workspace_id=workspace_id,
        dataset_name=dataset_name,
        version_tag=version_tag,
        status="exported",
        manifest_json=manifest,
    )
    db.add(dataset)
    db.flush()

    for feedback_id, record in records_with_feedback:
        db.add(
            TrainingDatasetRecord(
                dataset_id=dataset.id,
                feedback_id=feedback_id,
                record_json=record,
            )
        )
    db.commit()

    logger.info(
        "Exported dataset %s for workspace %s with %s records",
        dataset_name,
        workspace_id,
        len(records),
    )

    return {
        "dataset_name": dataset_name,
        "version_tag": version_tag,
        "record_count": len(records),
        "dataset_path": str(dataset_file),
        "manifest_path": str(manifest_file),
        "manifest": manifest,
    }
