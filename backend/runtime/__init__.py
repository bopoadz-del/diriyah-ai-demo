"""Self-Coding Runtime System for Diriyah Brain AI.

This module provides:
- CodeGenerator: LLM-powered code generation from natural language
- SandboxExecutor: Safe code execution with RestrictedPython
- FunctionRegistry: Pre-approved analytical functions
- ContextBuilder: Project context assembly for code generation
"""

from backend.runtime.schemas import (
    ApprovedFunction,
    CodeRequest,
    ExecutionHistory,
    ExecutionResult,
)

__all__ = [
    "ApprovedFunction",
    "CodeRequest",
    "ExecutionHistory",
    "ExecutionResult",
]
