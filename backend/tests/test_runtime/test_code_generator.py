"""Tests for the CodeGenerator class."""

import pytest
from backend.runtime.code_generator import CodeGenerator, APPROVED_MODULES, FORBIDDEN_PATTERNS


class TestCodeGenerator:
    """Test the CodeGenerator class."""

    def test_init_default(self):
        """Test default initialization."""
        generator = CodeGenerator()
        assert generator._model == "gpt-4"

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        generator = CodeGenerator(model="gpt-3.5-turbo")
        assert generator._model == "gpt-3.5-turbo"

    def test_generate_fallback_sum(self):
        """Test fallback code generation for sum queries."""
        generator = CodeGenerator()
        code = generator._generate_fallback_code(
            "Calculate the total sum of all values",
            {"values": [1, 2, 3, 4, 5]},
        )
        assert "sum" in code.lower()
        assert "result" in code

    def test_generate_fallback_variance(self):
        """Test fallback code generation for variance queries."""
        generator = CodeGenerator()
        code = generator._generate_fallback_code(
            "What if prices increase by 20%?",
            {"boq_items": []},
        )
        assert "variance" in code.lower() or "percentage" in code.lower()
        assert "result" in code

    def test_generate_fallback_monte_carlo(self):
        """Test fallback code generation for Monte Carlo queries."""
        generator = CodeGenerator()
        code = generator._generate_fallback_code(
            "Run Monte Carlo simulation",
            {"values": [100, 200, 300]},
        )
        assert "monte carlo" in code.lower() or "simulation" in code.lower() or "numpy" in code.lower()
        assert "result" in code


class TestCodeValidation:
    """Test code validation."""

    def test_validate_safe_code(self):
        """Test validation of safe code."""
        generator = CodeGenerator()
        code = """
import pandas as pd
import numpy as np

result = pd.DataFrame({'a': [1, 2, 3]}).mean()
"""
        validation = generator.validate_code(code)
        assert validation["is_safe"] is True
        assert len(validation["violations"]) == 0
        assert "pandas" in validation["approved_imports"]
        assert "numpy" in validation["approved_imports"]

    def test_validate_unsafe_import_os(self):
        """Test validation rejects os import."""
        generator = CodeGenerator()
        code = """
import os
result = os.system('ls')
"""
        validation = generator.validate_code(code)
        assert validation["is_safe"] is False
        assert "os" in validation["forbidden_imports"]

    def test_validate_unsafe_import_subprocess(self):
        """Test validation rejects subprocess import."""
        generator = CodeGenerator()
        code = """
import subprocess
result = subprocess.run(['ls'])
"""
        validation = generator.validate_code(code)
        assert validation["is_safe"] is False
        assert "subprocess" in validation["forbidden_imports"]

    def test_validate_forbidden_eval(self):
        """Test validation rejects eval."""
        generator = CodeGenerator()
        code = """
result = eval('1+1')
"""
        validation = generator.validate_code(code)
        assert validation["is_safe"] is False
        assert any("eval" in v for v in validation["violations"])

    def test_validate_forbidden_exec(self):
        """Test validation rejects exec."""
        generator = CodeGenerator()
        code = """
exec('print("hello")')
result = None
"""
        validation = generator.validate_code(code)
        assert validation["is_safe"] is False
        assert any("exec" in v for v in validation["violations"])

    def test_validate_forbidden_open(self):
        """Test validation rejects open."""
        generator = CodeGenerator()
        code = """
f = open('/etc/passwd', 'r')
result = f.read()
"""
        validation = generator.validate_code(code)
        assert validation["is_safe"] is False
        assert any("open" in v for v in validation["violations"])


class TestImportExtraction:
    """Test import extraction."""

    def test_extract_imports_simple(self):
        """Test extracting simple imports."""
        generator = CodeGenerator()
        code = """
import pandas
import numpy
"""
        imports = generator.extract_imports(code)
        assert "pandas" in imports
        assert "numpy" in imports

    def test_extract_imports_from(self):
        """Test extracting from imports."""
        generator = CodeGenerator()
        code = """
from datetime import datetime
from collections import Counter
"""
        imports = generator.extract_imports(code)
        assert "datetime" in imports
        assert "collections" in imports

    def test_extract_imports_mixed(self):
        """Test extracting mixed imports."""
        generator = CodeGenerator()
        code = """
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
"""
        imports = generator.extract_imports(code)
        assert "pandas" in imports
        assert "numpy" in imports
        assert "datetime" in imports
        assert "collections" in imports


class TestApprovedModules:
    """Test approved modules list."""

    def test_approved_modules_contains_pandas(self):
        """Test pandas is approved."""
        assert "pandas" in APPROVED_MODULES

    def test_approved_modules_contains_numpy(self):
        """Test numpy is approved."""
        assert "numpy" in APPROVED_MODULES

    def test_approved_modules_contains_statistics(self):
        """Test statistics is approved."""
        assert "statistics" in APPROVED_MODULES

    def test_approved_modules_does_not_contain_os(self):
        """Test os is not approved."""
        assert "os" not in APPROVED_MODULES

    def test_approved_modules_does_not_contain_sys(self):
        """Test sys is not approved."""
        assert "sys" not in APPROVED_MODULES


class TestForbiddenPatterns:
    """Test forbidden patterns list."""

    def test_forbidden_patterns_contains_eval(self):
        """Test eval is forbidden."""
        assert "eval" in FORBIDDEN_PATTERNS

    def test_forbidden_patterns_contains_exec(self):
        """Test exec is forbidden."""
        assert "exec" in FORBIDDEN_PATTERNS

    def test_forbidden_patterns_contains_import(self):
        """Test __import__ is forbidden."""
        assert "__import__" in FORBIDDEN_PATTERNS

    def test_forbidden_patterns_contains_os(self):
        """Test os. is forbidden."""
        assert "os." in FORBIDDEN_PATTERNS
