"""Tests for the SandboxExecutor class."""

import pytest
from backend.runtime.sandbox import SandboxExecutor, APPROVED_MODULES, FORBIDDEN_PATTERNS


class TestSandboxExecutor:
    """Test the SandboxExecutor class."""

    def test_init_default(self):
        """Test default initialization."""
        executor = SandboxExecutor()
        assert executor._timeout == 5
        assert executor._memory_limit == 256 * 1024 * 1024

    def test_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        executor = SandboxExecutor(timeout=10)
        assert executor._timeout == 10

    def test_execute_simple_sum(self):
        """Test executing simple sum calculation."""
        executor = SandboxExecutor()
        code = """
result = sum([1, 2, 3, 4, 5])
"""
        result = executor.execute(code, {})
        assert result.status == "success"
        assert result.output == 15

    def test_execute_with_context(self):
        """Test executing code with context."""
        executor = SandboxExecutor()
        code = """
result = sum(values)
"""
        result = executor.execute(code, {"values": [10, 20, 30]})
        assert result.status == "success"
        assert result.output == 60

    def test_execute_with_pandas(self):
        """Test executing code with pandas."""
        executor = SandboxExecutor()
        code = """
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3]})
result = df['a'].sum()
"""
        result = executor.execute(code, {})
        assert result.status == "success"
        assert result.output == 6

    def test_execute_with_numpy(self):
        """Test executing code with numpy."""
        executor = SandboxExecutor()
        code = """
import numpy as np
arr = np.array([1, 2, 3, 4, 5])
result = float(np.mean(arr))
"""
        result = executor.execute(code, {})
        assert result.status == "success"
        assert result.output == 3.0

    def test_execute_dict_result(self):
        """Test executing code that returns a dict."""
        executor = SandboxExecutor()
        code = """
result = {'total': 100, 'count': 5, 'average': 20}
"""
        result = executor.execute(code, {})
        assert result.status == "success"
        assert result.output == {"total": 100, "count": 5, "average": 20}

    def test_execute_error_handling(self):
        """Test that errors are caught properly."""
        executor = SandboxExecutor()
        code = """
result = 1 / 0
"""
        result = executor.execute(code, {})
        assert result.status == "error"
        assert "ZeroDivision" in result.error_message

    def test_execute_syntax_error(self):
        """Test that syntax errors are caught."""
        executor = SandboxExecutor()
        code = """
result = [1, 2, 3
"""
        result = executor.execute(code, {})
        assert result.status == "error"


class TestSandboxSafety:
    """Test sandbox safety features."""

    def test_reject_os_import(self):
        """Test that os import is rejected."""
        executor = SandboxExecutor()
        code = """
import os
result = os.getcwd()
"""
        result = executor.execute(code, {})
        assert result.status == "error"
        assert any("forbidden" in str(result.error_message).lower() or "os" in str(result.error_message).lower() for _ in [1])

    def test_reject_subprocess(self):
        """Test that subprocess is rejected."""
        executor = SandboxExecutor()
        code = """
import subprocess
result = subprocess.run(['ls'])
"""
        result = executor.execute(code, {})
        assert result.status == "error"

    def test_reject_eval(self):
        """Test that eval is rejected."""
        executor = SandboxExecutor()
        code = """
result = eval('1+1')
"""
        result = executor.execute(code, {})
        assert result.status == "error"

    def test_reject_exec(self):
        """Test that exec is rejected."""
        executor = SandboxExecutor()
        code = """
exec('result = 42')
"""
        result = executor.execute(code, {})
        assert result.status == "error"

    def test_reject_open(self):
        """Test that open is rejected."""
        executor = SandboxExecutor()
        code = """
f = open('/etc/passwd')
result = f.read()
"""
        result = executor.execute(code, {})
        assert result.status == "error"

    def test_reject_dunder_import(self):
        """Test that __import__ is rejected."""
        executor = SandboxExecutor()
        code = """
os = __import__('os')
result = os.getcwd()
"""
        result = executor.execute(code, {})
        assert result.status == "error"


class TestCodeValidation:
    """Test static code validation."""

    def test_validate_safe_code(self):
        """Test validation of safe code."""
        result = SandboxExecutor.validate_code("""
import pandas as pd
result = pd.DataFrame()
""")
        assert result["is_safe"] is True
        assert "pandas" in result["approved_imports"]

    def test_validate_unsafe_code(self):
        """Test validation of unsafe code."""
        result = SandboxExecutor.validate_code("""
import os
result = os.system('ls')
""")
        assert result["is_safe"] is False
        assert "os" in result["forbidden_imports"]

    def test_validate_mixed_imports(self):
        """Test validation with mixed imports."""
        result = SandboxExecutor.validate_code("""
import pandas
import os
import numpy
result = None
""")
        assert result["is_safe"] is False
        assert "pandas" in result["approved_imports"]
        assert "numpy" in result["approved_imports"]
        assert "os" in result["forbidden_imports"]


class TestViolationChecking:
    """Test violation checking."""

    def test_check_violations_empty(self):
        """Test no violations for safe code."""
        executor = SandboxExecutor()
        violations = executor._check_violations("""
import pandas
result = 42
""")
        assert len(violations) == 0

    def test_check_violations_forbidden_import(self):
        """Test forbidden import detection."""
        executor = SandboxExecutor()
        violations = executor._check_violations("""
import socket
result = None
""")
        assert len(violations) > 0
        assert any("socket" in v for v in violations)

    def test_check_violations_forbidden_pattern(self):
        """Test forbidden pattern detection."""
        executor = SandboxExecutor()
        violations = executor._check_violations("""
result = eval('1+1')
""")
        assert len(violations) > 0
        assert any("eval" in v for v in violations)


class TestApprovedModulesList:
    """Test the approved modules list."""

    def test_contains_pandas(self):
        assert "pandas" in APPROVED_MODULES

    def test_contains_numpy(self):
        assert "numpy" in APPROVED_MODULES

    def test_contains_datetime(self):
        assert "datetime" in APPROVED_MODULES

    def test_contains_statistics(self):
        assert "statistics" in APPROVED_MODULES

    def test_contains_math(self):
        assert "math" in APPROVED_MODULES

    def test_contains_json(self):
        assert "json" in APPROVED_MODULES

    def test_contains_collections(self):
        assert "collections" in APPROVED_MODULES

    def test_contains_re(self):
        assert "re" in APPROVED_MODULES

    def test_contains_itertools(self):
        assert "itertools" in APPROVED_MODULES

    def test_not_contains_os(self):
        assert "os" not in APPROVED_MODULES

    def test_not_contains_sys(self):
        assert "sys" not in APPROVED_MODULES

    def test_not_contains_subprocess(self):
        assert "subprocess" not in APPROVED_MODULES
