"""Unit tests for Middleware: hook execution, ordering, data modification."""

from __future__ import annotations

import pytest

from generative_ai_workflow import (
    AbortError,
    LLMNode,
    MockLLMProvider,
    PluginRegistry,
    Workflow,
    WorkflowConfig,
    WorkflowEngine,
    WorkflowStatus,
)
from generative_ai_workflow.middleware.base import Middleware
from generative_ai_workflow.providers.base import LLMRequest, LLMResponse, TokenUsage


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    PluginRegistry.clear()
    mock = MockLLMProvider(responses={"default": "Test response."})
    PluginRegistry.register_provider("mock", mock)
    yield


@pytest.fixture
def simple_workflow() -> Workflow:
    return Workflow(
        nodes=[LLMNode(name="gen", prompt="Hello {text}", provider="mock")],
        config=WorkflowConfig(provider="mock"),
    )


class TestMiddlewareHookOrder:
    """Verify FIFO middleware execution order."""

    async def test_hooks_execute_in_registration_order(
        self, simple_workflow: Workflow
    ) -> None:
        execution_order = []

        class RecordMiddleware(Middleware):
            def __init__(self, label: str):
                self.label = label

            async def on_workflow_start(self, wf_id, ctx):
                execution_order.append(f"start:{self.label}")

            async def on_workflow_end(self, result, ctx):
                execution_order.append(f"end:{self.label}")

        engine = WorkflowEngine()
        engine.use(RecordMiddleware("A")).use(RecordMiddleware("B")).use(RecordMiddleware("C"))
        await engine.run_async(simple_workflow, {"text": "x"})

        assert execution_order == [
            "start:A", "start:B", "start:C",
            "end:A", "end:B", "end:C",
        ]


class TestMiddlewareDataModification:
    """Verify middleware can modify/observe data."""

    async def test_on_workflow_end_receives_result(
        self, simple_workflow: Workflow
    ) -> None:
        received_results = []

        class CaptureMiddleware(Middleware):
            async def on_workflow_end(self, result, ctx):
                received_results.append(result.status)

        engine = WorkflowEngine()
        engine.use(CaptureMiddleware())
        await engine.run_async(simple_workflow, {"text": "y"})

        assert len(received_results) == 1
        assert received_results[0] == WorkflowStatus.COMPLETED


class TestMiddlewareErrorIsolation:
    """Verify middleware errors don't crash the workflow."""

    async def test_middleware_exception_does_not_abort_workflow(
        self, simple_workflow: Workflow
    ) -> None:
        class BrokenMiddleware(Middleware):
            async def on_workflow_start(self, wf_id, ctx):
                raise RuntimeError("middleware exploded!")

        engine = WorkflowEngine()
        engine.use(BrokenMiddleware())
        # Workflow should still complete despite broken middleware
        result = await engine.run_async(simple_workflow, {"text": "z"})
        assert result.status == WorkflowStatus.COMPLETED


class TestPluginIsolation:
    """Verify plugin (node) failures are properly isolated."""

    async def test_non_critical_plugin_failure_isolated(self) -> None:
        """Non-critical node failure logged, execution continues."""
        from generative_ai_workflow import TransformNode

        workflow = Workflow(
            nodes=[
                TransformNode(
                    name="optional",
                    transform=lambda _: (_ for _ in ()).throw(RuntimeError("plugin error")),
                    is_critical=False,
                ),
                TransformNode(name="continue", transform=lambda _: {"ran": True}),
            ],
        )

        engine = WorkflowEngine()
        result = await engine.run_async(workflow, {})
        assert result.status == WorkflowStatus.COMPLETED
        assert result.metrics.steps_failed == 1
