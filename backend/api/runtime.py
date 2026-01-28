"""FastAPI router for the Self-Coding Runtime System."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

try:
    from sqlalchemy.orm import Session
    from backend.backend.db import get_db
except ImportError:
    Session = None
    get_db = None

from backend.runtime.schemas import (
    ApprovedFunction,
    CodeRequest,
    CodeValidation,
    ExecutionHistory,
    ExecutionResult,
    GenerateResponse,
)
from backend.runtime.sandbox import SandboxExecutor
from backend.runtime.function_registry import list_functions, APPROVED_FUNCTIONS
from backend.runtime.schemas import ExecutionLog

router = APIRouter()


def _get_runtime_service():
    """Lazy import runtime service."""
    from backend.services.runtime_service import RuntimeService
    return RuntimeService()


@router.post("/runtime/execute", response_model=ExecutionResult)
async def execute_code_query(
    request: CodeRequest,
    db: Session = Depends(get_db) if get_db else None,
):
    """Generate and execute code from natural language query.

    Args:
        request: Code execution request with query and context.
        db: Database session.

    Returns:
        ExecutionResult with generated code and output.
    """
    try:
        service = _get_runtime_service()
        result = await service.process_query(request, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runtime/generate", response_model=GenerateResponse)
async def generate_code_only(
    request: CodeRequest,
    db: Session = Depends(get_db) if get_db else None,
):
    """Generate code without executing (dry run).

    Args:
        request: Code generation request.
        db: Database session.

    Returns:
        GenerateResponse with generated code and validation.
    """
    try:
        service = _get_runtime_service()
        code = await service.generate_code(
            query=request.query,
            project_id=request.project_id,
            context=request.context or {},
            db=db,
        )

        # Validate the generated code
        validation_result = SandboxExecutor.validate_code(code)

        return GenerateResponse(
            generated_code=code,
            validation=CodeValidation(**validation_result),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runtime/history/{project_id}", response_model=List[ExecutionHistory])
async def get_execution_history(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db) if get_db else None,
):
    """Get execution history for a project.

    Args:
        project_id: Project ID.
        limit: Maximum number of records to return.
        db: Database session.

    Returns:
        List of ExecutionHistory records.
    """
    try:
        service = _get_runtime_service()
        history = await service.get_history(project_id, limit, db)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runtime/functions", response_model=List[ApprovedFunction])
async def list_approved_functions():
    """List all approved analytical functions.

    Returns:
        List of ApprovedFunction metadata.
    """
    functions = list_functions()
    return [
        ApprovedFunction(
            name=f["name"],
            signature=f["signature"],
            description=f["description"],
            risk_level=f["risk_level"],
            max_runtime=f["max_runtime"],
        )
        for f in functions
    ]


class ValidateRequest(BaseModel):
    """Request body for code validation."""
    code: str


@router.post("/runtime/validate", response_model=CodeValidation)
async def validate_code(request: ValidateRequest):
    """Validate code for safety without executing.

    Args:
        request: Request containing code to validate.

    Returns:
        CodeValidation result.
    """
    validation = SandboxExecutor.validate_code(request.code)
    return CodeValidation(**validation)


@router.delete("/runtime/execution/{execution_id}")
async def delete_execution(
    execution_id: int,
    db: Session = Depends(get_db) if get_db else None,
):
    """Delete an execution record.

    Args:
        execution_id: Execution record ID.
        db: Database session.

    Returns:
        Success status.
    """
    try:
        if db is None:
            return {"status": "ok", "message": "Database not available"}

        from backend.runtime.models import CodeExecution

        execution = db.query(CodeExecution).filter(
            CodeExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        db.delete(execution)
        db.commit()

        return {"status": "ok", "deleted_id": execution_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runtime/execution/{execution_id}", response_model=ExecutionResult)
async def get_execution(
    execution_id: int,
    db: Session = Depends(get_db) if get_db else None,
):
    """Get details of a specific execution.

    Args:
        execution_id: Execution record ID.
        db: Database session.

    Returns:
        ExecutionResult with full details.
    """
    try:
        if db is None:
            raise HTTPException(status_code=503, detail="Database not available")

        from backend.runtime.models import CodeExecution

        execution = db.query(CodeExecution).filter(
            CodeExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return ExecutionResult(
            execution_id=execution.id,
            generated_code=execution.generated_code,
            output=execution.result_json,
            execution_time=execution.execution_time,
            memory_used=execution.memory_used,
            status=execution.status,
            error_message=execution.error_message,
            logs=[
                ExecutionLog(
                    level=log.log_level,
                    message=log.message,
                    timestamp=log.timestamp,
                )
                for log in execution.logs
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runtime/function/{function_name}")
async def execute_approved_function(
    function_name: str,
    params: dict,
):
    """Execute an approved function directly.

    Args:
        function_name: Name of the approved function.
        params: Parameters to pass to the function.

    Returns:
        Function result.
    """
    if function_name not in APPROVED_FUNCTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Function '{function_name}' not found in registry",
        )

    try:
        func = APPROVED_FUNCTIONS[function_name]["function"]
        result = func(**params)
        return {"status": "ok", "result": result}
    except TypeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameters: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Execution error: {str(e)}",
        )
