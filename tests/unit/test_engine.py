"""Unit tests for WorkflowEngine: async/sync execution, timeout, cancellation."""

from __future__ import annotations

import asyncio
import time

import pytest

from generative_ai_workflow import (
    LLMNode,
    MockLLMProvider,
    PluginRegistry,
    TransformNode,
    Workflow,
    WorkflowConfig,
    WorkflowEngine,
    WorkflowStatus,
)


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    PluginRegistry.clear()
    mock = MockLLMProvider(responses={"default": "Engine test response."})
    PluginRegistry.register_provider("mock", mock)
    yield


@pytest.fixture
def simple_workflow() -> Workflow:
    return Workflow(
        nodes=[LLMNode(name="gen", prompt="Hello {text}", provider="mock")],
        config=WorkflowConfig(provider="mock"),
    )


class TestAsyncExecution:
    """Tests for async workflow execution (FR-006)."""

    async def test_execute_async_returns_completed(self, simple_workflow: Workflow) -> None:
        engine = WorkflowEngine()
        result = await engine.run_async(simple_workflow, {"text": "world"})
        assert result.status == WorkflowStatus.COMPLETED
        assert result.output is not None

    async def test_execute_async_correlation_id_auto_generated(
        self, simple_workflow: Workflow
    ) -> None:
        engine = WorkflowEngine()
        result = await engine.run_async(simple_workflow, {"text": "x"})
        assert len(result.correlation_id) == 36  # UUID

    async def test_execute_async_custom_correlation_id(self, simple_workflow: Workflow) -> None:
        engine = WorkflowEngine()
        result = await engine.run_async(
            simple_workflow, {"text": "x"}, correlation_id="trace-123"
        )
        assert result.correlation_id == "trace-123"

    async def test_result_preserved_after_completion(self, simple_workflow: Workflow) -> None:
        """Result must be preserved after workflow completes (async scenario)."""
        engine = WorkflowEngine()
        result = await engine.run_async(simple_workflow, {"text": "y"})
        # Access result multiple times — should still be accessible
        assert result.status == WorkflowStatus.COMPLETED
        assert result.workflow_id is not None


class TestSyncExecution:
    """Tests for synchronous workflow execution (FR-006, FR-007)."""

    def test_execute_sync_returns_completed(self, simple_workflow: Workflow) -> None:
        engine = WorkflowEngine()
        result = engine.run(simple_workflow, {"text": "world"})
        assert result.status == WorkflowStatus.COMPLETED

    def test_execute_sync_with_timeout_completes_fast(self, simple_workflow: Workflow) -> None:
        """Workflow that completes before timeout returns completed."""
        engine = WorkflowEngine()
        result = engine.run(simple_workflow, {"text": "x"}, timeout=30.0)
        assert result.status == WorkflowStatus.COMPLETED

    def test_execute_sync_timeout_exceeded(self) -> None:
        """Workflow exceeding timeout returns TIMEOUT status."""
        async def slow_transform(data: dict) -> dict:
            await asyncio.sleep(5)  # 5 seconds
            return {"done": True}

        # Use a TransformNode that sleeps
        class SlowNode(TransformNode):
            async def execute_async(self, context):
                from generative_ai_workflow.workflow import NodeResult, NodeStatus
                import uuid
                await asyncio.sleep(5)
                return NodeResult(
                    step_id=str(uuid.uuid4()),
                    status=NodeStatus.COMPLETED,
                    output={"done": True},
                    duration_ms=5000.0,
                )

        workflow = Workflow(nodes=[SlowNode(name="slow", transform=lambda d: d)])
        engine = WorkflowEngine()
        start = time.perf_counter()
        result = engine.run(workflow, {}, timeout=0.1)
        elapsed = time.perf_counter() - start

        assert result.status == WorkflowStatus.TIMEOUT
        assert elapsed < 2.0  # Should not wait 5 seconds
        assert "timed out" in result.error.lower()


class TestWorkflowEngineMiddleware:
    """Tests for middleware registration and method chaining."""

    def test_use_returns_self_for_chaining(self, simple_workflow: Workflow) -> None:
        from generative_ai_workflow.middleware.base import Middleware

        class NoOpMiddleware(Middleware):
            pass

        engine = WorkflowEngine()
        result_engine = engine.use(NoOpMiddleware()).use(NoOpMiddleware())
        assert result_engine is engine

    async def test_middleware_hooks_called(self, simple_workflow: Workflow) -> None:
        from generative_ai_workflow.middleware.base import Middleware

        calls = []

        class RecordingMiddleware(Middleware):
            async def on_workflow_start(self, workflow_id, context):
                calls.append("start")

            async def on_workflow_end(self, result, context):
                calls.append("end")

        engine = WorkflowEngine()
        engine.use(RecordingMiddleware())
        await engine.run_async(simple_workflow, {"text": "x"})
        assert calls == ["start", "end"]


class TestMetricsCollection:
    """Tests for execution metrics collection."""

    async def test_step_durations_recorded(self, simple_workflow: Workflow) -> None:
        engine = WorkflowEngine()
        result = await engine.run_async(simple_workflow, {"text": "x"})
        assert "gen" in result.metrics.step_durations
        assert result.metrics.step_durations["gen"] >= 0.0

    async def test_total_duration_recorded(self, simple_workflow: Workflow) -> None:
        engine = WorkflowEngine()
        result = await engine.run_async(simple_workflow, {"text": "x"})
        assert result.metrics.total_duration_ms >= 0.0

    async def test_token_usage_aggregated(self, simple_workflow: Workflow) -> None:
        engine = WorkflowEngine()
        result = await engine.run_async(simple_workflow, {"text": "x"})
        assert result.metrics.token_usage_total is not None
        assert result.metrics.token_usage_total.total_tokens > 0
