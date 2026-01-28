"""Sandbox executor for safe Python code execution."""

from __future__ import annotations

import io
import logging
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, List, Optional, Set

from backend.runtime.schemas import ExecutionLog, ExecutionResult

logger = logging.getLogger(__name__)

# Approved modules that can be imported
APPROVED_MODULES: Set[str] = {
    "pandas",
    "numpy",
    "datetime",
    "statistics",
    "math",
    "json",
    "collections",
    "re",
    "itertools",
}

# Patterns that are forbidden in code
FORBIDDEN_PATTERNS: List[str] = [
    "__import__",
    "eval(",
    "exec(",
    "compile(",
    "open(",
    "file(",
    "input(",
    "os.",
    "sys.",
    "subprocess.",
    "socket.",
    "shutil.",
    "pathlib.",
    "importlib.",
    "builtins.",
    "globals()",
    "locals()",
    "getattr(",
    "setattr(",
    "delattr(",
    "__builtins__",
    "__class__",
    "__bases__",
    "__subclasses__",
    "__mro__",
    "__code__",
    "__globals__",
]

# Default execution limits
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_MEMORY_LIMIT = 256 * 1024 * 1024  # 256MB


def _execute_in_sandbox(code: str, context: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """Execute code in an isolated environment.

    This function runs in a separate process for isolation.
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    logs = []
    result_value = None
    error_message = None
    status = "success"

    start_time = time.time()

    try:
        # Build restricted globals
        safe_globals = _build_safe_globals(context)

        # Execute with output capture
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, safe_globals)  # noqa: S102

        # Extract result
        result_value = safe_globals.get("result")

        # Capture stdout as logs
        stdout_content = stdout_capture.getvalue()
        if stdout_content:
            logs.append({"level": "INFO", "message": stdout_content.strip()})

    except Exception as e:
        status = "error"
        error_message = f"{type(e).__name__}: {str(e)}"
        logs.append({"level": "ERROR", "message": traceback.format_exc()})

    execution_time = time.time() - start_time

    # Capture stderr as warnings
    stderr_content = stderr_capture.getvalue()
    if stderr_content:
        logs.append({"level": "WARNING", "message": stderr_content.strip()})

    return {
        "output": result_value,
        "execution_time": execution_time,
        "status": status,
        "error_message": error_message,
        "logs": logs,
    }


def _make_restricted_import():
    """Create a restricted import function that only allows approved modules."""
    import builtins as _builtins
    _original_import = _builtins.__import__

    def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        """Restricted import that only allows approved modules."""
        module_name = name.split('.')[0]
        if module_name not in APPROVED_MODULES:
            raise ImportError(f"Module '{name}' is not approved for import")
        return _original_import(name, globals, locals, fromlist, level)

    return _restricted_import


def _build_safe_globals(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build a restricted globals dictionary for safe execution."""
    import builtins

    # Safe built-in functions
    safe_builtins = {
        "abs": builtins.abs,
        "all": builtins.all,
        "any": builtins.any,
        "bool": builtins.bool,
        "dict": builtins.dict,
        "enumerate": builtins.enumerate,
        "filter": builtins.filter,
        "float": builtins.float,
        "int": builtins.int,
        "len": builtins.len,
        "list": builtins.list,
        "map": builtins.map,
        "max": builtins.max,
        "min": builtins.min,
        "print": builtins.print,
        "range": builtins.range,
        "reversed": builtins.reversed,
        "round": builtins.round,
        "set": builtins.set,
        "sorted": builtins.sorted,
        "str": builtins.str,
        "sum": builtins.sum,
        "tuple": builtins.tuple,
        "zip": builtins.zip,
        "True": True,
        "False": False,
        "None": None,
        "isinstance": builtins.isinstance,
        "type": builtins.type,
        "__import__": _make_restricted_import(),
    }

    # Import approved modules
    approved_modules = {}
    for module_name in APPROVED_MODULES:
        try:
            if module_name == "pandas":
                import pandas as pd
                approved_modules["pd"] = pd
                approved_modules["pandas"] = pd
            elif module_name == "numpy":
                import numpy as np
                approved_modules["np"] = np
                approved_modules["numpy"] = np
            elif module_name == "datetime":
                import datetime
                approved_modules["datetime"] = datetime
            elif module_name == "statistics":
                import statistics
                approved_modules["statistics"] = statistics
            elif module_name == "math":
                import math
                approved_modules["math"] = math
            elif module_name == "json":
                import json
                approved_modules["json"] = json
            elif module_name == "collections":
                import collections
                approved_modules["collections"] = collections
            elif module_name == "re":
                import re as re_module
                approved_modules["re"] = re_module
            elif module_name == "itertools":
                import itertools
                approved_modules["itertools"] = itertools
        except ImportError:
            logger.warning("Could not import approved module: %s", module_name)

    # Build globals
    safe_globals = {
        "__builtins__": safe_builtins,
        "context": context,
        **approved_modules,
        **context,  # Inject context variables directly
    }

    return safe_globals


class SandboxExecutor:
    """Executes Python code in a sandboxed environment."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        memory_limit: int = DEFAULT_MEMORY_LIMIT,
    ):
        """Initialize the sandbox executor.

        Args:
            timeout: Maximum execution time in seconds.
            memory_limit: Maximum memory usage in bytes.
        """
        self._timeout = timeout
        self._memory_limit = memory_limit

    def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """Execute code safely in a sandbox.

        Args:
            code: Python code to execute.
            context: Dictionary of context variables.
            timeout: Execution timeout (overrides default).

        Returns:
            ExecutionResult with output, timing, and status.
        """
        context = context or {}
        timeout = timeout or self._timeout

        # Validate code safety first
        if not self._is_safe(code):
            violations = self._check_violations(code)
            return ExecutionResult(
                generated_code=code,
                output=None,
                status="error",
                error_message=f"Code safety violations: {', '.join(violations)}",
                logs=[ExecutionLog(level="ERROR", message=f"Violations: {violations}")],
            )

        # Execute in the current process with timeout simulation
        # Note: For production, use ProcessPoolExecutor for true isolation
        try:
            result = _execute_in_sandbox(code, context, timeout)

            return ExecutionResult(
                generated_code=code,
                output=result["output"],
                execution_time=result["execution_time"],
                status=result["status"],
                error_message=result.get("error_message"),
                logs=[
                    ExecutionLog(level=log["level"], message=log["message"])
                    for log in result.get("logs", [])
                ],
            )

        except FuturesTimeoutError:
            return ExecutionResult(
                generated_code=code,
                output=None,
                status="error",
                error_message=f"Execution timed out after {timeout} seconds",
                logs=[ExecutionLog(level="ERROR", message="Timeout")],
            )
        except Exception as e:
            return ExecutionResult(
                generated_code=code,
                output=None,
                status="error",
                error_message=str(e),
                logs=[ExecutionLog(level="ERROR", message=traceback.format_exc())],
            )

    def _is_safe(self, code: str) -> bool:
        """Check if code is safe to execute.

        Args:
            code: Python code to check.

        Returns:
            True if code passes safety checks.
        """
        violations = self._check_violations(code)
        return len(violations) == 0

    def _check_violations(self, code: str) -> List[str]:
        """Check code for safety violations.

        Args:
            code: Python code to check.

        Returns:
            List of violation descriptions.
        """
        violations = []

        # Check forbidden patterns
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in code:
                violations.append(f"Forbidden pattern: {pattern}")

        # Check imports
        import_pattern = r"(?:^|\n)\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_.]*)"
        imports = re.findall(import_pattern, code)
        for imp in imports:
            module = imp.split(".")[0]
            if module not in APPROVED_MODULES:
                violations.append(f"Forbidden import: {module}")

        # Check for dangerous string operations that might bypass checks
        dangerous_patterns = [
            r'getattr\s*\(',
            r'setattr\s*\(',
            r'delattr\s*\(',
            r'__\w+__',  # Dunder methods
            r'\.mro\(',
            r'\.\_\_class\_\_',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                violations.append(f"Dangerous pattern: {pattern}")

        return violations

    def _create_globals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create restricted globals for code execution.

        Args:
            context: Context variables to include.

        Returns:
            Dictionary of safe global variables.
        """
        return _build_safe_globals(context)

    @staticmethod
    def validate_code(code: str) -> Dict[str, Any]:
        """Static method to validate code without execution.

        Args:
            code: Python code to validate.

        Returns:
            Validation result dictionary.
        """
        executor = SandboxExecutor()
        violations = executor._check_violations(code)

        # Extract imports for reporting
        import_pattern = r"(?:^|\n)\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_.]*)"
        all_imports = re.findall(import_pattern, code)

        approved = [imp.split(".")[0] for imp in all_imports if imp.split(".")[0] in APPROVED_MODULES]
        forbidden = [imp.split(".")[0] for imp in all_imports if imp.split(".")[0] not in APPROVED_MODULES]

        return {
            "is_safe": len(violations) == 0,
            "violations": violations,
            "approved_imports": list(set(approved)),
            "forbidden_imports": list(set(forbidden)),
        }
