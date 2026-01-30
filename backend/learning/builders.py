"""Dataset builders for learning exports."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional

from backend.learning.models import FeedbackEvent


class DatasetBuilder:
    def __init__(
        self,
        name: str,
        event_types: Iterable[str],
        label_type: str,
        build_record: Callable[[FeedbackEvent, Optional[str]], Optional[Dict[str, Any]]],
    ) -> None:
        self.name = name
        self.event_types = tuple(event_types)
        self.label_type = label_type
        self.build_record = build_record


def _base_record(feedback: FeedbackEvent, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "feedback_id": feedback.id,
        "workspace_id": feedback.workspace_id,
        "event_type": feedback.event_type,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        "payload": payload,
    }


def _build_intent_routing(
    feedback: FeedbackEvent, label_value: Optional[str]
) -> Optional[Dict[str, Any]]:
    if not label_value:
        return None
    payload = dict(feedback.event_payload or {})
    record = _base_record(feedback, payload)
    record.update(
        {
            "input": payload.get("input") or payload.get("utterance"),
            "expected_intent": label_value,
        }
    )
    return record


def _build_tool_routing(
    feedback: FeedbackEvent, label_value: Optional[str]
) -> Optional[Dict[str, Any]]:
    if not label_value:
        return None
    payload = dict(feedback.event_payload or {})
    record = _base_record(feedback, payload)
    record.update(
        {
            "input": payload.get("input") or payload.get("utterance"),
            "expected_tool": label_value,
        }
    )
    return record


def _build_ule_linking(
    feedback: FeedbackEvent, label_value: Optional[str]
) -> Optional[Dict[str, Any]]:
    if not label_value:
        return None
    payload = dict(feedback.event_payload or {})
    record = _base_record(feedback, payload)
    record.update(
        {
            "source_entity": payload.get("source_entity"),
            "target_entity": payload.get("target_entity"),
            "link_decision": label_value,
        }
    )
    return record


DATASET_BUILDERS: Dict[str, DatasetBuilder] = {
    "intent_routing": DatasetBuilder(
        name="intent_routing",
        event_types=["intent_routing"],
        label_type="intent",
        build_record=_build_intent_routing,
    ),
    "tool_routing": DatasetBuilder(
        name="tool_routing",
        event_types=["tool_routing"],
        label_type="tool",
        build_record=_build_tool_routing,
    ),
    "ule_linking": DatasetBuilder(
        name="ule_linking",
        event_types=["ule_linking"],
        label_type="ule_link",
        build_record=_build_ule_linking,
    ),
}
