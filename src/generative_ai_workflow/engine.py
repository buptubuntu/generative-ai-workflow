"""WorkflowEngine: executes workflows with async/sync support, retry, and middleware.

The engine is the central execution component. It coordinates step execution,
state transitions, error handling, timeout management, and metric collection.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from generative_ai_workflow.exceptions import WorkflowError
from generative_ai_workflow.observability.logging import configure_logging, get_logger
from generative_ai_workflow.workflow import (
    ExecutionMetrics,
    NodeContext,
    NodeStatus,
    WorkflowConfig,
    WorkflowResult,
    WorkflowStatus,
    _validate_input_data,
)

if TYPE_CHECKING:
    from generative_ai_workflow.config import FrameworkConfig
    from generative_ai_workflow.middleware.base import Middleware
    from generative_ai_workflow.workflow import Workflow

logger = get_logger("generative_ai_workflow.engine")


class WorkflowEngine:
    """Execute workflows through the full middleware pipeline.

    Central execution engine with middleware, retry, observability, and
    both async and sync execution modes.

    Args:
        config: Optional FrameworkConfig. Loads from environment if not provided.

    Example::

        engine = WorkflowEngine()
        engine.use(CostTrackingMiddleware())
        result = await engine.run_async(workflow, {"text": "..."})
    """

    def __init__(self, config: "FrameworkConfig | None" = None) -> None:
        if config is None:
            from generative_ai_workflow.config import FrameworkConfig
            config = FrameworkConfig()
        self._config = config
        self._middleware: list["Middleware"] = []
        configure_logging(config.log_level)

    def use(self, middleware: "Middleware") -> "WorkflowEngine":
        """Register middleware executed in FIFO registration order.

        Args:
            middleware: Middleware instance to add to the pipeline.

        Returns:
            Self for method chaining: engine.use(A).use(B).use(C)
        """
        self._middleware.append(middleware)
        return self

    async def run_async(
        self,
        workflow: "Workflow",
        input_data: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> WorkflowResult:
        """Execute a workflow asynchronously through the full middleware pipeline.

        Args:
            workflow: Workflow to execute.
            input_data: Input data passed to the first step.
            correlation_id: Optional tracing ID. Auto-generated if not provided.

        Returns:
            WorkflowResult with status, output, and metrics.
        """
        cid = correlation_id or str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        # Validate input for injection patterns
        try:
            _validate_input_data(input_data)
        except ValueError as e:
            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                correlation_id=cid,
                status=WorkflowStatus.FAILED,
                output=None,
                error=f"Input validation failed: {e}",
                metrics=ExecutionMetrics(),
                created_at=created_at,
                completed_at=datetime.now(timezone.utc),
            )

        # Fire on_workflow_start middleware hooks
        ctx: dict[str, Any] = {
            "workflow_id": workflow.workflow_id,
            "correlation_id": cid,
            "workflow_name": workflow.name,
        }
        for mw in self._middleware:
            try:
                await mw.on_workflow_start(workflow.workflow_id, ctx)
            except Exception as e:
                logger.warning("middleware.on_workflow_start.error", error=str(e))

        logger.info(
            "workflow.started",
            workflow_id=workflow.workflow_id,
            correlation_id=cid,
            workflow_name=workflow.name,
            status=WorkflowStatus.RUNNING.value,
        )

        result = await self._execute_nodes(
            workflow, input_data, cid, created_at, ctx
        )

        # Fire on_workflow_end middleware hooks
        for mw in self._middleware:
            try:
                await mw.on_workflow_end(result, ctx)
            except Exception as e:
                logger.warning("middleware.on_workflow_end.error", error=str(e))

        logger.info(
            "workflow.completed",
            workflow_id=result.workflow_id,
            correlation_id=result.correlation_id,
            status=result.status.value,
            duration_ms=round(result.metrics.total_duration_ms, 2),
            total_tokens=(
                result.metrics.token_usage_total.total_tokens
                if result.metrics.token_usage_total
                else 0
            ),
            steps_completed=result.metrics.steps_completed,
        )

        return result

    async def _execute_nodes(
        self,
        workflow: "Workflow",
        input_data: dict[str, Any],
        correlation_id: str,
        created_at: datetime,
        ctx: dict[str, Any],
    ) -> WorkflowResult:
        """Execute all nodes sequentially, accumulating outputs."""
        wall_start = time.perf_counter()
        previous_outputs: dict[str, Any] = {}
        node_results = []
        metrics = ExecutionMetrics()

        workflow_config = workflow.config

        for node in workflow.nodes:
            step_id = str(uuid.uuid4())
            node_ctx = NodeContext(
                workflow_id=workflow.workflow_id,
                step_id=step_id,
                correlation_id=correlation_id,
                input_data=input_data,
                variables={},
                previous_outputs=previous_outputs.copy(),
                config=workflow_config,
            )

            logger.debug(
                "node.started",
                workflow_id=workflow.workflow_id,
                node_name=node.name,
                step_id=step_id,
            )

            try:
                node_result = await node.execute_async(node_ctx)
            except Exception as e:
                node_result_data = {
                    "step_id": step_id,
                    "status": NodeStatus.FAILED,
                    "output": None,
                    "error": str(e),
                    "duration_ms": 0.0,
                    "token_usage": None,
                }
                from generative_ai_workflow.workflow import NodeResult
                node_result = NodeResult(**node_result_data)

            # Record metrics
            metrics.step_durations[node.name] = node_result.duration_ms
            if node_result.token_usage is not None:
                metrics.step_token_usage[node.name] = node_result.token_usage
                if metrics.token_usage_total is None:
                    metrics.token_usage_total = node_result.token_usage
                else:
                    from generative_ai_workflow.providers.base import TokenUsage
                    prev = metrics.token_usage_total
                    metrics.token_usage_total = TokenUsage(
                        prompt_tokens=prev.prompt_tokens + node_result.token_usage.prompt_tokens,
                        completion_tokens=prev.completion_tokens + node_result.token_usage.completion_tokens,
                        total_tokens=prev.total_tokens + node_result.token_usage.total_tokens,
                        model=node_result.token_usage.model,
                        provider=node_result.token_usage.provider,
                    )

            logger.debug(
                "node.completed",
                workflow_id=workflow.workflow_id,
                node_name=node.name,
                status=node_result.status.value,
                duration_ms=round(node_result.duration_ms, 2),
            )

            if node_result.status == NodeStatus.FAILED:
                metrics.steps_failed += 1
                if node.is_critical:
                    # Fire node error hooks
                    exc = WorkflowError(node_result.error or "Node failed")
                    for mw in self._middleware:
                        try:
                            await mw.on_node_error(exc, node.name, ctx)
                        except Exception as mw_e:
                            logger.warning("middleware.on_node_error.error", error=str(mw_e))

                    total_duration = (time.perf_counter() - wall_start) * 1000
                    metrics.total_duration_ms = total_duration
                    return WorkflowResult(
                        workflow_id=workflow.workflow_id,
                        correlation_id=correlation_id,
                        status=WorkflowStatus.FAILED,
                        output=None,
                        error=f"Node '{node.name}' failed: {node_result.error}",
                        metrics=metrics,
                        created_at=created_at,
                        completed_at=datetime.now(timezone.utc),
                    )
                else:
                    metrics.steps_skipped += 1
            else:
                metrics.steps_completed += 1
                if node_result.output:
                    previous_outputs.update(node_result.output)

            node_results.append(node_result)

        total_duration = (time.perf_counter() - wall_start) * 1000
        metrics.total_duration_ms = total_duration

        return WorkflowResult(
            workflow_id=workflow.workflow_id,
            correlation_id=correlation_id,
            status=WorkflowStatus.COMPLETED,
            output=previous_outputs if previous_outputs else None,
            error=None,
            metrics=metrics,
            created_at=created_at,
            completed_at=datetime.now(timezone.utc),
        )

    def run(
        self,
        workflow: "Workflow",
        input_data: dict[str, Any],
        *,
        timeout: float | None = None,
        correlation_id: str | None = None,
    ) -> WorkflowResult:
        """Execute a workflow synchronously (blocking) with optional timeout.

        Args:
            workflow: Workflow to execute.
            input_data: Input data passed to the first step.
            timeout: Optional timeout in seconds. If exceeded, returns
                     WorkflowResult with status=TIMEOUT.
            correlation_id: Optional tracing ID. Auto-generated if not provided.

        Returns:
            WorkflowResult with status, output, and metrics.
        """
        from generative_ai_workflow._internal.async_utils import run_sync

        if timeout is None:
            return run_sync(self.run_async(workflow, input_data, correlation_id=correlation_id))

        # Wrap with asyncio.wait_for for timeout enforcement
        async def _with_timeout() -> WorkflowResult:
            cid = correlation_id or str(uuid.uuid4())
            try:
                return await asyncio.wait_for(
                    self.run_async(workflow, input_data, correlation_id=cid),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "workflow.timeout",
                    workflow_id=workflow.workflow_id,
                    correlation_id=cid,
                    timeout_seconds=timeout,
                )
                return WorkflowResult(
                    workflow_id=workflow.workflow_id,
                    correlation_id=cid,
                    status=WorkflowStatus.TIMEOUT,
                    output=None,
                    error=f"Workflow timed out after {timeout}s",
                    metrics=ExecutionMetrics(),
                    created_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                )

        return run_sync(_with_timeout())
