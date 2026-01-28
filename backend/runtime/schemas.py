"""Pydantic schemas for the Self-Coding Runtime System."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CodeRequest(BaseModel):
    """Request to generate and execute code from natural language."""

    query: str = Field(..., description="Natural language query to convert to code")
    project_id: Optional[int] = Field(None, description="Project ID for context")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    dry_run: bool = Field(False, description="Generate code without executing")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What's the cost variance if steel prices increase 15%?",
                "project_id": 1,
                "dry_run": False,
            }
        }


class ExecutionLog(BaseModel):
    """Log entry from code execution."""

    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionResult(BaseModel):
    """Result of code execution."""

    execution_id: Optional[int] = Field(None, description="Execution record ID")
    generated_code: str = Field(..., description="Generated Python code")
    output: Optional[Any] = Field(None, description="Execution output")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    memory_used: Optional[int] = Field(None, description="Memory used in bytes")
    status: str = Field(..., description="Execution status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    logs: List[ExecutionLog] = Field(default_factory=list, description="Execution logs")

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": 42,
                "generated_code": "import pandas as pd\nresult = {'total': 100}",
                "output": {"total": 100},
                "execution_time": 0.023,
                "memory_used": 2457600,
                "status": "success",
                "error_message": None,
                "logs": [],
            }
        }


class ApprovedFunction(BaseModel):
    """Schema for approved analytical functions."""

    name: str = Field(..., description="Function name")
    signature: str = Field(..., description="Function signature")
    description: str = Field(..., description="Function description")
    risk_level: str = Field("low", description="Risk level: low, medium, high")
    max_runtime: float = Field(5.0, description="Maximum runtime in seconds")


class ExecutionHistory(BaseModel):
    """Summary of past execution for history listing."""

    id: int = Field(..., description="Execution ID")
    query: str = Field(..., description="Original query")
    status: str = Field(..., description="Execution status")
    created_at: datetime = Field(..., description="Execution timestamp")
    execution_time: Optional[float] = Field(None, description="Execution time")


class CodeValidation(BaseModel):
    """Result of code safety validation."""

    is_safe: bool = Field(..., description="Whether the code is safe to execute")
    violations: List[str] = Field(default_factory=list, description="Safety violations found")
    approved_imports: List[str] = Field(default_factory=list, description="Approved imports used")
    forbidden_imports: List[str] = Field(default_factory=list, description="Forbidden imports found")


class GenerateResponse(BaseModel):
    """Response for generate-only (dry run) requests."""

    generated_code: str = Field(..., description="Generated Python code")
    validation: CodeValidation = Field(..., description="Code validation result")
