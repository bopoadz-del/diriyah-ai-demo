"""Content scanner for detecting prohibited patterns and malicious content."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import re
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .schemas import ScanResult, Severity, PatternType
from .models import ProhibitedPattern

logger = logging.getLogger(__name__)

_TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


# Default prohibited patterns
PROHIBITED_PATTERNS = {
    "pii": {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "password": r"password\s*[:=]\s*\S+",
        "api_key": r"(api[_-]?key|apikey)\s*[:=]\s*['\"]?[\w\-]+['\"]?",
        "token": r"(access[_-]?token|bearer)\s*[:=]\s*['\"]?[\w\-\.]+['\"]?",
    },
    "sql_injection": {
        "union_select": r"\b(union|union\s+all)\s+select\b",
        "sql_keywords": r"\b(drop|delete|insert|update)\s+(table|database|from)\b",
        "sql_comment": r"(--|#|\/\*|\*\/)",
        "sql_quotes": r"'[\s]*or[\s]*'[\s]*=[\s]*'",
        "sql_semicolon": r";[\s]*(drop|delete|insert|update)",
    },
    "xss": {
        "script_tag": r"<script[^>]*>.*?<\s*/\s*script[^>]*>",
        "javascript": r"javascript:",
        "event_handler": r"on\w+\s*=",
        "iframe": r"<iframe[^>]*>",
        "object_tag": r"<object[^>]*>",
        "embed_tag": r"<embed[^>]*>",
    },
    "command_injection": {
        "shell_commands": r";\s*(rm|wget|curl|bash|sh|cat|ls|chmod|chown)\b",
        "pipe_commands": r"\|[\s]*(rm|wget|curl|bash|sh|cat)",
        "redirect": r">[\s]*/",
        "backticks": r"`[^`]+`",
        "eval": r"\beval\s*\(",
    },
}


class ContentScanner:
    """
    Scans content for prohibited patterns and malicious content.
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize ContentScanner.
        
        Args:
            db: Optional database session to load patterns from DB
        """
        self.db = db
        self.patterns = PROHIBITED_PATTERNS.copy()
        self._ml_model = None
        self._ml_threshold = float(os.getenv("ML_SCANNER_THRESHOLD", "0.8"))
        
        if db:
            self.load_patterns()

        if _TORCH_AVAILABLE and os.getenv("ENABLE_ML_SCANNER", "false").lower() == "true":
            self._load_ml_model()
    
    def load_patterns(self) -> None:
        """Load additional prohibited patterns from database."""
        if not self.db:
            return
        
        db_patterns = self.db.query(ProhibitedPattern).filter(
            ProhibitedPattern.enabled == True
        ).all()
        
        for pattern in db_patterns:
            pattern_type = pattern.pattern_type
            
            if pattern_type not in self.patterns:
                self.patterns[pattern_type] = {}
            
            # Use pattern description as key or generate one
            key = pattern.description or f"pattern_{pattern.id}"
            self.patterns[pattern_type][key] = pattern.pattern_regex
    
    def scan(self, content: str) -> ScanResult:
        """
        Scan content for all prohibited patterns.
        
        Args:
            content: Text content to scan
            
        Returns:
            ScanResult with violations and severity
        """
        if not content:
            return ScanResult(safe=True, severity=Severity.LOW)
        
        violations = []
        max_severity = Severity.LOW
        details = {}
        
        # Check PII
        pii_violations = self.check_pii(content)
        if pii_violations:
            violations.extend([f"PII: {v}" for v in pii_violations])
            details["pii"] = ", ".join(pii_violations)
            max_severity = Severity.MEDIUM
        
        # Check SQL injection
        sql_violations = self.check_injection(content, "sql_injection")
        if sql_violations:
            violations.extend([f"SQL Injection: {v}" for v in sql_violations])
            details["sql_injection"] = ", ".join(sql_violations)
            max_severity = Severity.HIGH
        
        # Check XSS
        xss_violations = self.check_injection(content, "xss")
        if xss_violations:
            violations.extend([f"XSS: {v}" for v in xss_violations])
            details["xss"] = ", ".join(xss_violations)
            max_severity = Severity.HIGH
        
        # Check command injection
        cmd_violations = self.check_injection(content, "command_injection")
        if cmd_violations:
            violations.extend([f"Command Injection: {v}" for v in cmd_violations])
            details["command_injection"] = ", ".join(cmd_violations)
            max_severity = Severity.CRITICAL
        
        # Check malicious patterns
        malicious_violations = self.check_malicious(content)
        if malicious_violations:
            violations.extend([f"Malicious: {v}" for v in malicious_violations])
            details["malicious"] = ", ".join(malicious_violations)
            max_severity = Severity.CRITICAL

        ml_violation = self.check_ml(content)
        if ml_violation:
            violations.append(f"ML: {ml_violation['label']}")
            details["ml"] = f"{ml_violation['label']} ({ml_violation['score']:.2f})"
            max_severity = Severity.CRITICAL
        
        safe = len(violations) == 0
        
        return ScanResult(
            safe=safe,
            violations=violations,
            severity=max_severity,
            sanitized_text=None if safe else self._sanitize(content),
            details=details
        )

    def _load_ml_model(self) -> None:
        try:
            torch = importlib.import_module("torch")
            self._ml_model = torch.hub.load("unitary/toxic-bert", "toxic_bert")
        except Exception as exc:
            logger.warning("Failed to load ML content scanner model: %s", exc)
            self._ml_model = None

    def check_ml(self, content: str) -> Optional[Dict[str, float]]:
        if not self._ml_model or not content:
            return None
        try:
            results = self._ml_model(content)
        except Exception as exc:
            logger.warning("ML content scan failed: %s", exc)
            return None

        label = "ml_flagged"
        score = None
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                label = first.get("label", label)
                score = first.get("score")
            elif isinstance(first, list) and first and isinstance(first[0], dict):
                label = first[0].get("label", label)
                score = first[0].get("score")

        if score is None:
            return None
        if score >= self._ml_threshold:
            return {"label": str(label), "score": float(score)}
        return None
    
    def check_pii(self, content: str) -> List[str]:
        """
        Check for personally identifiable information (PII).
        
        Args:
            content: Text content to check
            
        Returns:
            List of detected PII pattern types
        """
        violations = []
        pii_patterns = self.patterns.get("pii", {})
        
        for pattern_name, pattern in pii_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(pattern_name)
        
        return violations
    
    def check_injection(self, content: str, injection_type: str) -> List[str]:
        """
        Check for injection attacks (SQL, XSS, command).
        
        Args:
            content: Text content to check
            injection_type: Type of injection to check (sql_injection, xss, command_injection)
            
        Returns:
            List of detected injection pattern types
        """
        violations = []
        injection_patterns = self.patterns.get(injection_type, {})
        
        for pattern_name, pattern in injection_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(pattern_name)
        
        return violations
    
    def check_malicious(self, content: str) -> List[str]:
        """
        Check for other malicious patterns.
        
        Args:
            content: Text content to check
            
        Returns:
            List of detected malicious patterns
        """
        violations = []
        
        # Check for excessive special characters (possible obfuscation)
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', content)) / max(len(content), 1)
        if special_char_ratio > 0.3:
            violations.append("excessive_special_chars")
        
        # Check for null bytes
        if '\x00' in content:
            violations.append("null_bytes")
        
        # Check for excessive URL encoding
        url_encoded = re.findall(r'%[0-9A-Fa-f]{2}', content)
        if len(url_encoded) > 10:
            violations.append("excessive_url_encoding")
        
        # Check for base64 encoded content (potential payload)
        base64_pattern = r'(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?'
        if re.search(base64_pattern, content):
            violations.append("base64_payload")
        
        return violations
    
    def _sanitize(self, content: str) -> str:
        """
        Sanitize content by removing dangerous patterns.
        
        Args:
            content: Text content to sanitize
            
        Returns:
            Sanitized content
        """
        sanitized = content
        
        # Remove script tags (including with whitespace/attributes before closing bracket)
        sanitized = re.sub(r'<script[^>]*>.*?<\s*/\s*script[^>]*>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove event handlers
        sanitized = re.sub(r'on\w+\s*=\s*["\']?[^"\']*["\']?', '', sanitized, flags=re.IGNORECASE)
        
        # Remove javascript: protocol
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        # Remove SQL comments
        sanitized = re.sub(r'(--|#|\/\*|\*\/)', '', sanitized)
        
        # Remove iframe, object, embed tags (including with whitespace/attributes before closing bracket)
        sanitized = re.sub(r'<(iframe|object|embed)[^>]*>.*?<\s*/\s*\1[^>]*>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        return sanitized
    
    def add_pattern(
        self,
        pattern_type: PatternType,
        pattern_regex: str,
        severity: Severity,
        description: str = None
    ) -> bool:
        """
        Add a new prohibited pattern to the database.
        
        Args:
            pattern_type: Type of pattern (PII, SQL_INJECTION, XSS, COMMAND_INJECTION)
            pattern_regex: Regular expression pattern
            severity: Severity level
            description: Optional description
            
        Returns:
            True if added successfully
        """
        if not self.db:
            return False
        
        try:
            # Validate regex
            re.compile(pattern_regex)
            
            new_pattern = ProhibitedPattern(
                pattern_type=pattern_type.value,
                pattern_regex=pattern_regex,
                severity=severity.value,
                enabled=True,
                description=description
            )
            
            self.db.add(new_pattern)
            self.db.commit()
            
            # Reload patterns
            self.load_patterns()
            
            return True
        except Exception:
            self.db.rollback()
            return False
