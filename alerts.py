"""
alerts.py
----------

Provides a simple rule‑based alerting system.  Given extracted
snippets, it scans for key terms such as delays, insurance expiry,
safety and quality problems and returns descriptive alert messages.

You can extend the ``KEYWORDS`` dictionary to refine the rules and
adjust the severity levels.
"""

from typing import List, Dict, Any
import re

KEYWORDS = {
    "high": [
        "delay", "extension of time", "eot", "critical path", "liquidated damages", "lds", "terminate"
    ],
    "medium": [
        "insurance expiry", "policy expiry", "bond expiry", "ncr", "non‑conformance", "rfi", "vo", "variation"
    ],
    "low": [
        "material shortage", "procurement", "lead time", "shipping", "shop drawing", "long lead", "safety", "ppe"
    ],
}

def detect(text: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    lower = text.lower()
    for severity, kws in KEYWORDS.items():
        for k in kws:
            if k in lower:
                # capture a short context window
                m = re.search(rf".{{0,60}}{re.escape(k)}.{{0,60}}", lower)
                ctx = m.group(0) if m else k
                out.append({"severity": severity, "message": f"{k} mentioned… {ctx[:120]}"})
    return out

def generate_alerts(snippets: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    alerts: List[Dict[str, str]] = []
    for s in snippets[:12]:
        alerts.extend(detect(s["text"]))
    # deduplicate by message
    seen = set()
    unique: List[Dict[str, str]] = []
    for a in alerts:
        key = (a["severity"], a["message"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(a)
    return unique[:5]