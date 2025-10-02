"""Compliance monitoring utilities for project documentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class NormalisedRule:
    """Internal representation of a compliance rule."""

    rule_id: str
    description: str
    severity: str
    required_phrases: List[str]
    forbidden_phrases: List[str]
    recommendations: Optional[str] = None


def check_compliance(document_text: str, rules: List[Any]) -> List[Dict[str, Any]]:
    """Assess a document against governance rules.

    Parameters
    ----------
    document_text:
        Full text of the document being assessed.
    rules:
        A list of rule definitions.  Each rule can be a string (shorthand for a
        required phrase) or a dictionary with the following optional keys:

        ``id``
            Identifier for traceability in the UI.
        ``description``
            Human readable text describing the requirement.
        ``severity``
            ``low`` | ``medium`` | ``high`` – defaults to ``medium``.
        ``required_phrases``
            Iterable of phrases that must be present in ``document_text``.
        ``forbidden_phrases``
            Iterable of phrases that should *not* appear.
        ``recommendation``
            Suggested remediation message.

    Returns
    -------
    list
        Each element contains ``rule_id``, ``status`` (``compliant``,
        ``warning`` or ``violation``), ``severity`` and ``details`` providing
        context for dashboards.
    """

    if not document_text:
        document_text = ""

    text_lower = document_text.lower()
    findings: List[Dict[str, Any]] = []

    for raw_rule in rules or []:
        rule = _normalise_rule(raw_rule)
        missing = _missing_phrases(text_lower, rule.required_phrases)
        forbidden_hits = _present_phrases(text_lower, rule.forbidden_phrases)

        if missing and forbidden_hits:
            status = "violation"
            details = (
                f"Missing {', '.join(missing)} and detected forbidden phrases {', '.join(forbidden_hits)}"
            )
        elif missing:
            status = "violation"
            details = f"Missing required phrase(s): {', '.join(missing)}"
        elif forbidden_hits:
            status = "warning" if rule.severity == "low" else "violation"
            details = f"Forbidden phrase(s) present: {', '.join(forbidden_hits)}"
        else:
            status = "compliant"
            details = "Requirement satisfied"

        finding: Dict[str, Any] = {
            "rule_id": rule.rule_id,
            "description": rule.description,
            "status": status,
            "severity": rule.severity,
            "details": details,
        }

        if rule.recommendations and status != "compliant":
            finding["recommendation"] = rule.recommendations

        findings.append(finding)

    return findings


def _normalise_rule(raw_rule: Any) -> NormalisedRule:
    if isinstance(raw_rule, str):
        return NormalisedRule(
            rule_id=raw_rule,
            description=f"Document must mention '{raw_rule}'",
            severity="medium",
            required_phrases=[raw_rule],
            forbidden_phrases=[],
        )

    if not isinstance(raw_rule, dict):
        return NormalisedRule(
            rule_id="unknown",
            description="Unstructured rule",
            severity="low",
            required_phrases=[],
            forbidden_phrases=[],
        )

    return NormalisedRule(
        rule_id=str(raw_rule.get("id", raw_rule.get("rule_id", "rule"))),
        description=str(raw_rule.get("description", "Unnamed requirement")),
        severity=str(raw_rule.get("severity", "medium")),
        required_phrases=list(_ensure_iterable(raw_rule.get("required_phrases", []))),
        forbidden_phrases=list(_ensure_iterable(raw_rule.get("forbidden_phrases", []))),
        recommendations=raw_rule.get("recommendation"),
    )


def _ensure_iterable(value: Any) -> Iterable[str]:
    if isinstance(value, (list, tuple, set)):
        return value
    if value:
        return [value]
    return []


def _missing_phrases(text_lower: str, phrases: Iterable[str]) -> List[str]:
    return [phrase for phrase in phrases if phrase.lower() not in text_lower]


def _present_phrases(text_lower: str, phrases: Iterable[str]) -> List[str]:
    return [phrase for phrase in phrases if phrase.lower() in text_lower]
