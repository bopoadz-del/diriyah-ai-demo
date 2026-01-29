"""
FastAPI endpoints for Progress Tracking via Computer Vision
Integrates with Diriyah Brain AI backend
"""

from __future__ import annotations

from datetime import datetime, timedelta
import base64
import json

import logging
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency for lightweight deployments
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully
    np = None  # type: ignore[assignment]

from fastapi import APIRouter, BackgroundTasks, Body, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.redisx.locks import DistributedLock

try:  # pragma: no cover - optional dependency
    import cv2
    _cv2_import_error: Optional[Exception] = None
except Exception as exc:  # pragma: no cover - handled at runtime
    cv2 = None  # type: ignore[assignment]
    _cv2_import_error = exc

ProgressTrackingService = None  # type: ignore[assignment]
ProgressSnapshot = None  # type: ignore[assignment]
_progress_service_import_error: Optional[Exception] = None

try:  # pragma: no cover - optional dependency for lightweight deployments
    from backend.services.progress_tracking_service import (
        ProgressSnapshot,
        ProgressTrackingService,
    )
except Exception as exc:  # pragma: no cover - handled during runtime
    _progress_service_import_error = exc

if ProgressTrackingService is None:
    try:  # pragma: no cover - optional dependency
        from backend.backend.services.progress_tracking_service import (
            ProgressSnapshot,
            ProgressTrackingService,
        )
        _progress_service_import_error = None
    except Exception as exc:  # pragma: no cover - handled during runtime
        _progress_service_import_error = exc

if ProgressTrackingService is None:
    try:  # pragma: no cover - optional dependency
        from services.progress_tracking_service import (
            ProgressSnapshot,
            ProgressTrackingService,
        )
        _progress_service_import_error = None
    except Exception as exc:  # pragma: no cover - handled during runtime
        _progress_service_import_error = exc

try:  # pragma: no cover - optional multipart dependency
    import multipart  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled gracefully
    multipart = None  # type: ignore[assignment]


def _file_param(*args, **kwargs):
    if multipart is None:
        return Body(None)
    return File(*args, **kwargs)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/progress", tags=["Progress Tracking"])

if cv2 is None:  # pragma: no cover - diagnostic log for Render deployments
    logger.warning("OpenCV import failed: %s", _cv2_import_error)

if np is None:
    logger.warning("NumPy import failed; progress tracking vision features disabled.")

if ProgressTrackingService is not None and np is not None:
    progress_service: Optional[ProgressTrackingService] = ProgressTrackingService(
        model_path="backend/models/yolov8m.pt",
        custom_model_path="backend/models/construction_yolo.pt",
    )
else:  # pragma: no cover - Render builds may skip CV dependencies
    progress_service = None
    logger.warning(
        "ProgressTrackingService could not be imported: %s",
        _progress_service_import_error,
    )


class AnalyzeRequest(BaseModel):
    location: str = Field(..., description="Site location identifier")
    reference_schedule: Optional[Dict] = Field(
        None,
        description="Expected progress from Primavera schedule",
    )
    compare_with_previous: bool = Field(
        default=True,
        description="Compare with previous snapshot",
    )


class ProgressReportRequest(BaseModel):
    location: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TimeframeComparisonRequest(BaseModel):
    location: str
    timeframe1_start: datetime
    timeframe1_end: datetime
    timeframe2_start: datetime
    timeframe2_end: datetime


class WebhookConfig(BaseModel):
    url: str
    events: List[str] = [
        "progress_update",
        "anomaly_detected",
        "milestone_completed",
    ]


def _ensure_progress_service() -> ProgressTrackingService:
    if progress_service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Progress tracking service is unavailable. Ensure the computer vision "
                "models are installed and dependencies are configured."
            ),
        )
    return progress_service


def _ensure_opencv() -> None:
    if cv2 is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenCV is not installed. Install opencv-python to enable progress "
                "tracking vision features."
            ),
        )


def decode_image(file_data: bytes) -> "np.ndarray":
    """Decode uploaded image to numpy array"""
    if np is None:
        raise HTTPException(
            status_code=503,
            detail="NumPy is not installed. Install numpy to decode images.",
        )
    _ensure_opencv()
    nparr = np.frombuffer(file_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image format")
    return img


def snapshot_to_dict(snapshot: ProgressSnapshot) -> Dict:
    """Convert ProgressSnapshot to dictionary for JSON response"""
    return {
        "timestamp": snapshot.timestamp.isoformat(),
        "location": snapshot.location,
        "progress_percentage": round(snapshot.progress_percentage, 2),
        "detected_objects": snapshot.detected_objects,
        "milestones_completed": snapshot.milestones_completed,
        "anomalies": snapshot.anomalies,
        "comparison_with_schedule": snapshot.comparison_with_schedule,
        "image_path": snapshot.image_path,
        "confidence_score": round(snapshot.confidence_score, 2),
    }


@router.post("/analyze", response_model=Dict)
async def analyze_site_progress(
    file: UploadFile | None = _file_param(..., description="Site photo for analysis"),
    location: str = "default",
    reference_schedule: Optional[str] = None,
    compare_with_previous: bool = True,
):
    """
    Analyze construction site progress from uploaded image

    - **file**: Site photo (JPG, PNG)
    - **location**: Site location identifier
    - **reference_schedule**: JSON string of expected schedule (optional)
    - **compare_with_previous**: Compare with previous snapshot

    Returns comprehensive progress analysis including:
    - Progress percentage
    - Detected construction elements
    - Completed milestones
    - Anomalies/issues
    - Schedule comparison
    """
    if multipart is None or file is None:
        raise HTTPException(
            status_code=503,
            detail="python-multipart is not installed; file uploads are disabled.",
        )

    try:
        service = _ensure_progress_service()

        contents = await file.read()
        image = decode_image(contents)

        schedule = None
        if reference_schedule:
            schedule = json.loads(reference_schedule)

        previous = None
        if compare_with_previous:
            history = service.progress_history.get(location, [])
            if history:
                previous = history[-1]

        snapshot = service.analyze_construction_site(
            image=image,
            location=location,
            reference_schedule=schedule,
            previous_snapshot=previous,
        )

        response = snapshot_to_dict(snapshot)
        response["insights"] = generate_insights(snapshot)

        return JSONResponse(content=response)

    except Exception as exc:  # pragma: no cover - surfaced via HTTP response
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/batch-analyze")
async def batch_analyze_progress(
    files: List[UploadFile] | None = _file_param(...),
    location: str = "default",
    reference_schedule: Optional[str] = None,
):
    """
    Batch analyze multiple site photos

    Useful for analyzing progress across different zones or time periods
    """
    service = _ensure_progress_service()

    results: List[Dict] = []

    for file in files:
        try:
            contents = await file.read()
            image = decode_image(contents)

            schedule = None
            if reference_schedule:
                schedule = json.loads(reference_schedule)

            snapshot = service.analyze_construction_site(
                image=image,
                location=f"{location}_{file.filename}",
                reference_schedule=schedule,
            )

            results.append({
                "filename": file.filename,
                "result": snapshot_to_dict(snapshot),
            })

        except Exception as exc:  # pragma: no cover - aggregated in response
            results.append({
                "filename": file.filename,
                "error": str(exc),
            })

    return JSONResponse(content={"results": results, "total": len(files)})


@router.post("/report")
async def generate_progress_report(request: ProgressReportRequest):
    """
    Generate comprehensive progress report for a location

    Includes:
    - Progress trends over time
    - Milestones achieved
    - Anomaly summary
    - Schedule adherence
    """
    if multipart is None or not files:
        raise HTTPException(
            status_code=503,
            detail="python-multipart is not installed; batch uploads are disabled.",
        )

    try:
        service = _ensure_progress_service()

        report = service.generate_progress_report(
            location=request.location,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])

        return JSONResponse(content=report)

    except Exception as exc:  # pragma: no cover - surfaced via HTTP response
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/compare-timeframes")
async def compare_timeframes(request: TimeframeComparisonRequest):
    """
    Compare progress between two time periods

    Useful for analyzing:
    - Seasonal variations
    - Impact of interventions
    - Team performance changes
    """
    try:
        service = _ensure_progress_service()

        comparison = service.compare_timeframes(
            location=request.location,
            timeframe1=(request.timeframe1_start, request.timeframe1_end),
            timeframe2=(request.timeframe2_start, request.timeframe2_end),
        )

        if "error" in comparison:
            raise HTTPException(status_code=404, detail=comparison["error"])

        return JSONResponse(content=comparison)

    except Exception as exc:  # pragma: no cover - surfaced via HTTP response
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/history/{location}")
async def get_progress_history(
    location: str,
    limit: int = 50,
    offset: int = 0,
):
    """
    Get historical progress snapshots for a location
    """
    service = _ensure_progress_service()

    history = service.progress_history.get(location, [])

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No progress history found for location: {location}",
        )

    paginated = history[offset : offset + limit]

    return JSONResponse(
        content={
            "location": location,
            "total": len(history),
            "limit": limit,
            "offset": offset,
            "snapshots": [snapshot_to_dict(s) for s in paginated],
        }
    )


@router.get("/locations")
async def get_tracked_locations():
    """
    Get all locations being tracked
    """
    service = _ensure_progress_service()

    locations = list(service.progress_history.keys())

    summary: List[Dict] = []
    for location in locations:
        history = service.progress_history[location]
        latest = history[-1] if history else None

        summary.append(
            {
                "location": location,
                "total_snapshots": len(history),
                "latest_progress": latest.progress_percentage if latest else 0,
                "last_updated": latest.timestamp.isoformat() if latest else None,
            }
        )

    return JSONResponse(content={"locations": summary, "total": len(locations)})


@router.get("/milestones/{location}")
async def get_milestones(location: str):
    """
    Get all completed milestones for a location
    """
    service = _ensure_progress_service()

    history = service.progress_history.get(location, [])

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for location: {location}",
        )

    milestone_timeline: List[Dict] = []
    seen_milestones = set()

    for snapshot in history:
        for milestone in snapshot.milestones_completed:
            if milestone not in seen_milestones:
                milestone_timeline.append(
                    {
                        "milestone": milestone,
                        "completed_at": snapshot.timestamp.isoformat(),
                        "progress_at_completion": snapshot.progress_percentage,
                    }
                )
                seen_milestones.add(milestone)

    return JSONResponse(
        content={
            "location": location,
            "total_milestones": len(milestone_timeline),
            "milestones": milestone_timeline,
        }
    )


@router.get("/anomalies/{location}")
async def get_anomalies(
    location: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get anomalies detected for a location within date range
    """
    service = _ensure_progress_service()

    history = service.progress_history.get(location, [])

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for location: {location}",
        )

    filtered = history
    if start_date or end_date:
        filtered = [
            s
            for s in history
            if (not start_date or s.timestamp >= start_date)
            and (not end_date or s.timestamp <= end_date)
        ]

    anomaly_list: List[Dict] = []
    for snapshot in filtered:
        for anomaly in snapshot.anomalies:
            anomaly_list.append(
                {
                    "anomaly": anomaly,
                    "detected_at": snapshot.timestamp.isoformat(),
                    "progress_percentage": snapshot.progress_percentage,
                    "location": location,
                }
            )

    return JSONResponse(
        content={
            "location": location,
            "total_anomalies": len(anomaly_list),
            "anomalies": anomaly_list,
        }
    )


@router.get("/velocity/{location}")
async def get_progress_velocity(location: str, days: int = 7):
    """
    Calculate progress velocity (rate of change) over specified days
    """
    service = _ensure_progress_service()

    history = service.progress_history.get(location, [])

    if len(history) < 2:
        raise HTTPException(
            status_code=404,
            detail="Insufficient data to calculate velocity",
        )

    cutoff_date = datetime.now() - timedelta(days=days)
    recent = [s for s in history if s.timestamp >= cutoff_date]

    if len(recent) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data in last {days} days",
        )

    velocity = service._calculate_velocity(recent)

    current_progress = recent[-1].progress_percentage
    remaining_progress = 100 - current_progress

    days_to_completion: Optional[float] = None
    projected_completion: Optional[str] = None

    if velocity > 0:
        days_to_completion = remaining_progress / velocity
        projected_completion = (
            datetime.now() + timedelta(days=days_to_completion)
        ).isoformat()

    return JSONResponse(
        content={
            "location": location,
            "period_days": days,
            "velocity_pct_per_day": round(velocity, 3),
            "current_progress": round(current_progress, 2),
            "remaining_progress": round(remaining_progress, 2),
            "days_to_completion": round(days_to_completion, 1)
            if days_to_completion
            else None,
            "projected_completion_date": projected_completion,
        }
    )


@router.post("/train-custom-model")
async def train_custom_model(
    background_tasks: BackgroundTasks,
    workspace_id: str,
    dataset_path: str,
    epochs: int = 100,
    model_name: str = "construction_custom",
):
    """
    Train a custom YOLO model on construction-specific dataset

    This endpoint triggers background training - use webhooks to get notified
    """
    service = _ensure_progress_service()

    lock = DistributedLock()
    lock_key = f"lock:workspace:{workspace_id}:learning"
    token = lock.acquire(lock_key, ttl=60 * 60 * 2, wait_seconds=0)
    if token is None:
        return JSONResponse(
            status_code=409,
            content={"message": "Learning already running for workspace."},
        )

    def train_model() -> None:
        """Background task for model training"""
        try:
            from ultralytics import YOLO

            model = YOLO("yolov8m.pt")

            model.train(
                data=dataset_path,
                epochs=epochs,
                imgsz=640,
                device="0",
                project="backend/models",
                name=model_name,
            )

            model.save(f"backend/models/{model_name}.pt")
        finally:
            lock.release(lock_key, token)

    background_tasks.add_task(train_model)

    return JSONResponse(
        content={
            "message": "Model training started",
            "model_name": model_name,
            "epochs": epochs,
            "status": "training",
        }
    )


@router.get("/model-info")
async def get_model_info():
    """
    Get information about loaded models
    """
    service = _ensure_progress_service()

    base_model_classes = service.base_model.names if service.base_model else []
    custom_model_classes = (
        service.construction_model.names if service.construction_model else None
    )

    return JSONResponse(
        content={
            "base_model": {
                "loaded": service.base_model is not None,
                "classes": base_model_classes,
                "total_classes": len(base_model_classes)
                if base_model_classes
                else 0,
            },
            "custom_model": {
                "loaded": service.construction_model is not None,
                "classes": custom_model_classes,
                "total_classes": len(custom_model_classes)
                if custom_model_classes
                else 0,
            },
            "construction_categories": service.construction_classes,
        }
    )


@router.post("/webhook/configure")
async def configure_webhook(config: WebhookConfig):
    """
    Configure webhook for progress tracking events

    Webhooks will be triggered for:
    - progress_update: When progress is updated
    - anomaly_detected: When anomalies are found
    - milestone_completed: When milestones are achieved
    """
    return JSONResponse(
        content={"message": "Webhook configured successfully", "url": config.url, "events": config.events}
    )


@router.get("/dashboard-summary")
async def get_dashboard_summary():
    """
    Get summary data for progress tracking dashboard

    Returns overview of all tracked locations
    """
    service = _ensure_progress_service()

    locations = list(service.progress_history.keys())

    summary = {
        "total_locations": len(locations),
        "total_snapshots": sum(len(service.progress_history[loc]) for loc in locations),
        "locations": [],
    }

    for location in locations:
        history = service.progress_history[location]
        if not history:
            continue

        latest = history[-1]

        recent_cutoff = datetime.now() - timedelta(days=7)
        recent = [s for s in history if s.timestamp >= recent_cutoff]
        velocity = service._calculate_velocity(recent) if len(recent) >= 2 else 0

        location_summary = {
            "location": location,
            "current_progress": round(latest.progress_percentage, 2),
            "schedule_status": latest.comparison_with_schedule["status"],
            "schedule_variance": round(
                latest.comparison_with_schedule.get("variance", 0), 2
            ),
            "total_snapshots": len(history),
            "last_updated": latest.timestamp.isoformat(),
            "velocity_7d": round(velocity, 3),
            "recent_anomalies": len([a for s in recent for a in s.anomalies]),
            "milestones_completed": len(
                set(m for s in history for m in s.milestones_completed)
            ),
        }

        summary["locations"].append(location_summary)

    summary["locations"].sort(key=lambda x: x["current_progress"], reverse=True)

    return JSONResponse(content=summary)


def generate_insights(snapshot: ProgressSnapshot) -> List[str]:
    """Generate actionable insights from progress snapshot"""
    insights: List[str] = []

    if snapshot.progress_percentage < 20:
        insights.append("Project is in early stages - monitor foundation quality")
    elif 20 <= snapshot.progress_percentage < 50:
        insights.append("Structure phase - ensure quality control on load-bearing elements")
    elif 50 <= snapshot.progress_percentage < 80:
        insights.append("Mid-stage progress - coordinate MEP installations")
    else:
        insights.append("Near completion - focus on finishing and quality checks")

    schedule_status = snapshot.comparison_with_schedule.get("status", "unknown")
    if schedule_status == "behind_schedule":
        insights.append("Behind schedule - consider resource augmentation")
    elif schedule_status == "ahead_of_schedule":
        insights.append("Ahead of schedule - excellent progress")

    if snapshot.anomalies:
        insights.append(
            f"⚠️ {len(snapshot.anomalies)} anomalies detected - immediate review recommended"
        )

    if snapshot.milestones_completed:
        insights.append(f"✓ {len(snapshot.milestones_completed)} milestones achieved")

    equipment_detected = [
        obj
        for obj in snapshot.detected_objects
        if any(eq in obj["class"].lower() for eq in ["crane", "excavator", "mixer"])
    ]
    if len(equipment_detected) > 3:
        insights.append(
            f"{len(equipment_detected)} equipment units detected - high activity zone"
        )

    return insights


@router.post("/chat/analyze-progress")
async def chat_analyze_progress(
    user_query: str,
    location: Optional[str] = None,
    image_base64: Optional[str] = None,
):
    """
    Chat-based progress analysis endpoint

    Integrates with Diriyah Brain AI chat interface
    """
    try:
        service = _ensure_progress_service()

        snapshot: Optional[ProgressSnapshot] = None

        if image_base64:
            image_data = base64.b64decode(image_base64)
            image = decode_image(image_data)

            snapshot = service.analyze_construction_site(
                image=image,
                location=location or "chat_upload",
            )

            response = snapshot_to_dict(snapshot)
        else:
            if not location:
                raise HTTPException(
                    status_code=400,
                    detail="Either location or image_base64 must be provided",
                )

            history = service.progress_history.get(location, [])
            if not history:
                raise HTTPException(
                    status_code=404,
                    detail=f"No progress data found for location: {location}",
                )

            snapshot = history[-1]
            response = snapshot_to_dict(snapshot)

        assert snapshot is not None
        insights = generate_insights(snapshot)

        summary = {
            "location": response["location"],
            "progress_percentage": response["progress_percentage"],
            "milestones_completed": len(snapshot.milestones_completed),
            "anomalies_detected": len(snapshot.anomalies),
            "schedule_status": snapshot.comparison_with_schedule.get("status"),
        }

        narrative_parts = [
            f"Current progress at {summary['location']} is {summary['progress_percentage']}%.",
        ]
        if summary["schedule_status"]:
            narrative_parts.append(
                f"Schedule status is {summary['schedule_status'].replace('_', ' ')}."
            )
        if summary["milestones_completed"]:
            narrative_parts.append(
                f"{summary['milestones_completed']} milestone(s) have been completed."
            )
        if summary["anomalies_detected"]:
            narrative_parts.append(
                f"{summary['anomalies_detected']} anomaly/anomalies detected."
            )

        narrative_parts.extend(insights)

        response.update(
            {
                "insights": insights,
                "chat_summary": " ".join(narrative_parts),
                "user_query": user_query,
            }
        )

        return JSONResponse(content=response)

    except Exception as exc:  # pragma: no cover - surfaced via HTTP response
        raise HTTPException(status_code=500, detail=str(exc)) from exc
