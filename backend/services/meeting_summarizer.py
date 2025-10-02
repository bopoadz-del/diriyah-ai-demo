"""Generate structured meeting notes from raw transcripts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass
class ExtractedItem:
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    severity: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        payload = {"description": self.description}
        if self.owner:
            payload["owner"] = self.owner
        if self.due_date:
            payload["due_date"] = self.due_date
        if self.severity:
            payload["severity"] = self.severity
        return payload


def summarize_transcript(transcript: str) -> Dict[str, Any]:
    """Convert a transcript into digestible summary artefacts."""

    if not transcript or not transcript.strip():
        return {
            "summary": "",
            "decisions": [],
            "action_items": [],
            "issues": [],
        }

    sentences = _tokenise(transcript)
    decisions = _extract_items(sentences, {"decision", "decided", "approved", "approve"})
    action_items = _extract_items(
        sentences,
        {"action", "follow up", "assign", "deliver", "send", "prepare"},
        default_owner_keywords={"assigned to", "to "},
    )
    issues = _extract_items(
        sentences,
        {"issue", "risk", "concern", "blocker", "delay"},
        severity_keywords={"critical": "high", "major": "high", "minor": "low"},
    )

    summary = _build_summary(sentences, decisions, issues, action_items)

    return {
        "summary": summary,
        "decisions": [item.as_dict() for item in decisions],
        "action_items": [item.as_dict() for item in action_items],
        "issues": [item.as_dict() for item in issues],
    }


def _tokenise(transcript: str) -> List[str]:
    statements = [segment.strip() for segment in SENTENCE_SPLIT_RE.split(transcript) if segment.strip()]
    normalised: List[str] = []
    for statement in statements:
        cleaned = re.sub(r"^[A-Za-z ]{1,40}:\s*", "", statement)
        if cleaned:
            normalised.append(cleaned)
    return normalised


def _extract_items(
    sentences: Iterable[str],
    keywords: Iterable[str],
    *,
    default_owner_keywords: Optional[Iterable[str]] = None,
    severity_keywords: Optional[Dict[str, str]] = None,
) -> List[ExtractedItem]:
    extracted: List[ExtractedItem] = []
    keyword_list = [keyword.lower() for keyword in keywords]

    for sentence in sentences:
        lower_sentence = sentence.lower()
        if not any(keyword in lower_sentence for keyword in keyword_list):
            continue

        owner = _extract_owner(sentence, default_owner_keywords)
        due_date = _extract_due_date(sentence)
        severity = _extract_severity(lower_sentence, severity_keywords)
        extracted.append(
            ExtractedItem(
                description=_clean_description(sentence),
                owner=owner,
                due_date=due_date,
                severity=severity,
            )
        )

    return extracted


def _extract_owner(sentence: str, keywords: Optional[Iterable[str]]) -> Optional[str]:
    if not keywords:
        return None

    lower_sentence = sentence.lower()
    for keyword in keywords:
        keyword_lower = keyword.lower()
        index = lower_sentence.find(keyword_lower)
        if index == -1:
            continue
        tail = sentence[index + len(keyword_lower) :].strip()
        match = re.match(r"([A-Z][a-z]+(?: [A-Z][a-z]+)*)", tail)
        if match:
            return match.group(1)
    return None


def _extract_due_date(sentence: str) -> Optional[str]:
    match = re.search(
        r"\bby ([A-Za-z]+ \d{1,2}|end of [A-Za-z]+|next week|(?:Q[1-4]|Monday|Tuesday|Wednesday|Thursday|Friday))",
        sentence,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    match = re.search(r"\bby (\d{4}-\d{2}-\d{2})", sentence)
    if match:
        return match.group(1)
    return None


def _extract_severity(lower_sentence: str, severity_keywords: Optional[Dict[str, str]]) -> Optional[str]:
    if not severity_keywords:
        return None
    for keyword, severity in severity_keywords.items():
        if keyword in lower_sentence:
            return severity
    if "urgent" in lower_sentence or "immediate" in lower_sentence:
        return "high"
    return None


def _clean_description(sentence: str) -> str:
    sentence = sentence.strip()
    sentence = re.sub(r"\b(decision|decided|action|issue)[:\s]", "", sentence, flags=re.IGNORECASE)
    return sentence


def _build_summary(
    sentences: List[str],
    decisions: List[ExtractedItem],
    issues: List[ExtractedItem],
    action_items: List[ExtractedItem],
) -> str:
    highlights: List[str] = []

    if decisions:
        highlights.append(f"Key decisions: {', '.join(item.description for item in decisions[:2])}")

    if issues:
        highlights.append(f"Outstanding risks: {', '.join(item.description for item in issues[:2])}")

    if action_items:
        highlights.append(f"Next actions: {', '.join(item.description for item in action_items[:2])}")

    if not highlights:
        highlights = sentences[:2]

    return " ".join(highlights)
