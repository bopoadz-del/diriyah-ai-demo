import os
from typing import Iterable, List, Sequence

from fastapi import APIRouter

import openai


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
        openai.api_key = api_key
        response = openai.Model.list()
        ids = _collect_model_ids(response)
        return {"status": "ok", "models_available": ids}
    except Exception as e:
        return {"status": "error", "message": str(e)}
