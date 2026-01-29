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

try:  # pragma: no cover - optional dependency for lightweight deployments
    from backend.backend.services.progress_tracking_service import (
        ProgressSnapshot,
        ProgressTrackingService,
    )
    _progress_service_import_error: Optional[Exception] = None
except Exception as exc:  # pragma: no cover - handled during runtime
    ProgressTrackingService = None  # type: ignore[assignment]
    ProgressSnapshot = None  # type: ignore[assignment]
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
