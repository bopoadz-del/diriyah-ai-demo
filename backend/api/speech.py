"""Stub speech-to-text endpoints used for local development and tests."""

from __future__ import annotations

import io
import logging
from typing import Any, Callable, Optional

from fastapi import APIRouter, Body, File, HTTPException, UploadFile

router = APIRouter()
logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional multipart dependency
    import multipart  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled gracefully
    multipart = None  # type: ignore[assignment]


def _upload_param(*args, **kwargs):
    if multipart is None:
        return Body(None)
    return File(*args, **kwargs)


@router.get("/speech/diagnostics")
def speech_diagnostics() -> dict[str, str]:
    """Return a stubbed response indicating the speech pipeline is mocked."""

    return {"status": "stubbed", "detail": "Speech pipeline not available in tests"}


# Optional transcription backends -------------------------------------------------
try:  # pragma: no cover - optional dependency path
    from backend.services.speech_to_text import (
        transcribe_audio as _service_transcribe,
    )
except Exception:  # pragma: no cover - runtime optionality
    _service_transcribe: Optional[Callable[..., Any]] = None
else:  # pragma: no cover - imported when available
    _service_transcribe = _service_transcribe

try:  # pragma: no cover - optional dependency path
    from backend import speech_to_text as _module_speech
except Exception:  # pragma: no cover - runtime optionality
    _module_transcribe: Optional[Callable[..., Any]] = None
else:  # pragma: no cover - imported when available
    _module_transcribe = getattr(_module_speech, "transcribe_audio", None)

try:  # pragma: no cover - optional dependency path
    from backend.services.rag_memory import (
        retrieve_with_memory as _retrieve_with_memory,
    )
except Exception:  # pragma: no cover - runtime optionality
    _retrieve_with_memory: Optional[Callable[[str], Any]] = None
else:  # pragma: no cover - imported when available
    _retrieve_with_memory = _retrieve_with_memory


def _reset_upload_pointer(file: UploadFile) -> None:
    try:
        file.file.seek(0)
    except Exception:  # pragma: no cover - best effort reset
        pass


async def _read_upload(file: UploadFile) -> bytes:
    contents = await file.read()
    _reset_upload_pointer(file)
    return contents


def _make_buffer(contents: bytes, filename: str | None) -> io.BytesIO:
    buffer = io.BytesIO(contents)
    buffer.name = filename or "audio.wav"
    buffer.seek(0)
    return buffer


def _extract_transcript(result: Any) -> Optional[str]:
    if isinstance(result, str):
        cleaned = result.strip()
        return cleaned if cleaned else None
    if isinstance(result, dict):
        for key in ("transcript", "text", "message"):
            value = result.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
    return None


async def _transcribe(file: UploadFile) -> str:
    contents = await _read_upload(file)
    if not contents:
        return "No audio content received."

    filename = file.filename or "uploaded-audio"
    attempts: list[tuple[str, Callable[[], Any]]] = []

    def add_attempt(name: str, func: Optional[Callable[..., Any]], *args: Any, **kwargs: Any) -> None:
        if func is None:
            return
        attempts.append((name, lambda f=func, a=args, k=kwargs: f(*a, **k)))

    add_attempt(
        "backend.services.speech_to_text",
        _service_transcribe,
        _make_buffer(contents, filename),
    )
    add_attempt(
        "backend.speech_to_text",
        _module_transcribe,
        filename,
    )

    for name, call in attempts:
        try:
            result = call()
            transcript = _extract_transcript(result)
            if transcript:
                return transcript
        except Exception as exc:  # pragma: no cover - logging for troubleshooting
            logger.debug("Speech transcription via %s failed: %s", name, exc, exc_info=True)

    return "Transcription unavailable (stubbed)."


def _generate_answer(project_id: str, transcript: str) -> str:
    if _retrieve_with_memory is not None:
        try:
            rag_result = _retrieve_with_memory(transcript)
            if isinstance(rag_result, dict):
                answer = rag_result.get("answer")
                if isinstance(answer, str):
                    cleaned = answer.strip()
                    if cleaned:
                        return cleaned
        except Exception as exc:  # pragma: no cover - optional path
            logger.debug("RAG memory retrieval failed: %s", exc, exc_info=True)

    transcript_preview = (transcript or "").strip()
    if transcript_preview:
        snippet = transcript_preview[:160]
        if len(transcript_preview) > 160:
            snippet = snippet.rstrip() + "…"
        return (
            "(stub) Unable to query project knowledge base for"
            f" {project_id}. Transcript snippet: {snippet}"
        )

    return f"(stub) No transcript available to generate an answer for project {project_id}."


@router.post("/speech/{project_id}")
async def speech_to_text(
    project_id: str, file: UploadFile | None = _upload_param(...)
) -> dict[str, str]:
    """Transcribe uploaded audio and provide a stubbed answer for the project."""

    if multipart is None or file is None:
        raise HTTPException(
            status_code=503,
            detail="python-multipart is not installed; speech uploads are disabled.",
        )

    transcript = await _transcribe(file)
    answer = _generate_answer(project_id, transcript)
    return {"transcript": transcript, "answer": answer}
