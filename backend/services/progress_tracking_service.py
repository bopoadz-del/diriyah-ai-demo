"""Stub progress tracking service for lightweight deployments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ProgressSnapshot:
    timestamp: datetime
    location: str
    progress_percentage: float
    detected_objects: List[str]
    milestones_completed: List[str]
    anomalies: List[str]
    comparison_with_schedule: Dict[str, Any]
    image_path: Optional[str]
    confidence_score: float


class ProgressTrackingService:
    def __init__(self, model_path: str, custom_model_path: Optional[str] = None) -> None:
        self.model_path = model_path
        self.custom_model_path = custom_model_path
        self.progress_history: Dict[str, List[ProgressSnapshot]] = {}

    def analyze_construction_site(
        self,
        image: Any,
        location: str,
        reference_schedule: Optional[Dict[str, Any]] = None,
        previous_snapshot: Optional[ProgressSnapshot] = None,
    ) -> ProgressSnapshot:
        progress = 0.0
        if previous_snapshot:
            progress = min(previous_snapshot.progress_percentage + 5.0, 100.0)

        snapshot = ProgressSnapshot(
            timestamp=datetime.now(timezone.utc),
            location=location,
            progress_percentage=progress,
            detected_objects=[],
            milestones_completed=[],
            anomalies=[],
            comparison_with_schedule=reference_schedule or {},
            image_path=None,
            confidence_score=0.5,
        )
        self.progress_history.setdefault(location, []).append(snapshot)
        return snapshot
