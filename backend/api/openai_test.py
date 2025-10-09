from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Iterable, List, Sequence

from fastapi import APIRouter

try:  # pragma: no cover - optional dependency for local debugging
    import openai as _openai
except ModuleNotFoundError:  # pragma: no cover - handled gracefully in endpoint
    _openai = None


class _MissingModel:
    """Fallback model shim used when the OpenAI client is unavailable."""

    @staticmethod
    def list(*_args, **_kwargs):  # pragma: no cover - simple defensive stub
        raise RuntimeError("openai package not installed")


OPENAI_AVAILABLE = _openai is not None
openai = _openai or SimpleNamespace(api_key=None, Model=_MissingModel)


router = APIRouter()


def _as_sequence(data: object) -> Sequence[object]:
    if isinstance(data, (str, bytes)):
        return [data]
    if isinstance(data, Sequence):
        return data
    if isinstance(data, Iterable):
        return list(data)
    return []


def _collect_model_ids(response: object, limit: int = 3) -> List[str]:
    data: Sequence[object] = []
    if isinstance(response, dict):
        data = _as_sequence(response.get("data"))
    else:
        response_data = getattr(response, "data", None)
        if response_data is not None:
            data = _as_sequence(response_data)

    ids: List[str] = []
    for item in data:
        model_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
        if model_id:
            ids.append(model_id)
        if len(ids) >= limit:
            break
    return ids


@router.get("/openai/test")
def openai_test():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"status": "error", "message": "OPENAI_API_KEY not set"}

    try:
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai package not installed")
        openai.api_key = api_key
        response = openai.Model.list()
        ids = _collect_model_ids(response)
        return {"status": "ok", "models_available": ids}
    except Exception as e:
        return {"status": "error", "message": str(e)}
