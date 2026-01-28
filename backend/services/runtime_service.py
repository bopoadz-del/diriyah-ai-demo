"""Runtime service for code generation and execution."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.runtime.code_generator import CodeGenerator
from backend.runtime.context_builder import ContextBuilder
from backend.runtime.sandbox import SandboxExecutor
from backend.runtime.schemas import (
    CodeRequest,
    ExecutionHistory,
    ExecutionResult,
    ExecutionLog,
)

logger = logging.getLogger(__name__)


class RuntimeService:
    """Service for processing code generation and execution requests."""

    def __init__(self):
        """Initialize the runtime service."""
        self._generator = CodeGenerator()
        self._executor = SandboxExecutor()
        self._context_builder = ContextBuilder()

    async def process_query(
        self,
        request: CodeRequest,
        db=None,
    ) -> ExecutionResult:
        """Process a code generation and execution request.

        Args:
            request: CodeRequest with query and options.
            db: Optional database session.

        Returns:
            ExecutionResult with generated code and output.
        """
        logger.info("Processing query: %s", request.query[:100])

        # Build context
        context = self._context_builder.build_context(
            project_id=request.project_id,
            query=request.query,
            db=db,
        )

        # Merge with provided context
        if request.context:
            context.update(request.context)

        # Generate code
        code = self._generator.generate_code(request.query, context)
        logger.debug("Generated code:\n%s", code)

        # If dry run, just return the code without executing
        if request.dry_run:
            validation = self._generator.validate_code(code)
            return ExecutionResult(
                generated_code=code,
                output=None,
                status="dry_run",
                error_message=None if validation["is_safe"] else f"Violations: {validation['violations']}",
                logs=[],
            )

        # Validate code
        validation = self._generator.validate_code(code)
        if not validation["is_safe"]:
            return ExecutionResult(
                generated_code=code,
                output=None,
                status="error",
                error_message=f"Code validation failed: {validation['violations']}",
                logs=[
                    ExecutionLog(
                        level="ERROR",
                        message=f"Violations: {validation['violations']}",
                    )
                ],
            )

        # Execute code
        result = self._executor.execute(code, context)

        # Save to database if available
        execution_id = await self._save_execution(request, code, result, db)
        result.execution_id = execution_id

        return result

    async def generate_code(
        self,
        query: str,
        project_id: Optional[int],
        context: Dict[str, Any],
        db=None,
    ) -> str:
        """Generate code without executing.

        Args:
            query: Natural language query.
            project_id: Optional project ID.
            context: Additional context.
            db: Optional database session.

        Returns:
            Generated Python code.
        """
        # Build context from project
        full_context = self._context_builder.build_context(
            project_id=project_id,
            query=query,
            db=db,
        )
        full_context.update(context)

        return self._generator.generate_code(query, full_context)

    async def execute_code(
        self,
        code: str,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """Execute pre-generated code.

        Args:
            code: Python code to execute.
            context: Execution context.

        Returns:
            ExecutionResult.
        """
        return self._executor.execute(code, context)

    async def get_history(
        self,
        project_id: int,
        limit: int,
        db=None,
    ) -> List[ExecutionHistory]:
        """Get execution history for a project.

        Args:
            project_id: Project ID.
            limit: Maximum records to return.
            db: Database session.

        Returns:
            List of ExecutionHistory records.
        """
        if db is None:
            # Return empty list if no database
            return []

        try:
            from backend.runtime.models import CodeExecution

            executions = (
                db.query(CodeExecution)
                .filter(CodeExecution.project_id == project_id)
                .order_by(CodeExecution.created_at.desc())
                .limit(limit)
                .all()
            )

            return [
                ExecutionHistory(
                    id=ex.id,
                    query=ex.query,
                    status=ex.status,
                    created_at=ex.created_at,
                    execution_time=ex.execution_time,
                )
                for ex in executions
            ]
        except Exception as e:
            logger.warning("Could not fetch history: %s", e)
            return []

    async def _save_execution(
        self,
        request: CodeRequest,
        code: str,
        result: ExecutionResult,
        db=None,
    ) -> Optional[int]:
        """Save execution record to database.

        Args:
            request: Original request.
            code: Generated code.
            result: Execution result.
            db: Database session.

        Returns:
            Execution record ID if saved.
        """
        if db is None:
            return None

        try:
            from backend.runtime.models import CodeExecution, ExecutionLog as LogModel

            execution = CodeExecution(
                project_id=request.project_id,
                query=request.query,
                generated_code=code,
                result_json=result.output,
                status=result.status,
                execution_time=result.execution_time,
                memory_used=result.memory_used,
                error_message=result.error_message,
            )

            db.add(execution)
            db.flush()  # Get ID

            # Save logs
            for log in result.logs:
                log_entry = LogModel(
                    execution_id=execution.id,
                    log_level=log.level,
                    message=log.message,
                    timestamp=log.timestamp,
                )
                db.add(log_entry)

            db.commit()
            return execution.id

        except Exception as e:
            logger.warning("Could not save execution: %s", e)
            if db:
                db.rollback()
            return None


# Singleton instance
_runtime_service: Optional[RuntimeService] = None


def get_runtime_service() -> RuntimeService:
    """Get or create the runtime service singleton.

    Returns:
        RuntimeService instance.
    """
    global _runtime_service
    if _runtime_service is None:
        _runtime_service = RuntimeService()
    return _runtime_service
