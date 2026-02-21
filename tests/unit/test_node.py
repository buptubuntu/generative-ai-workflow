"""Unit tests for WorkflowNode, LLMNode, and TransformNode."""

from __future__ import annotations

import pytest

from generative_ai_workflow import (
    LLMNode,
    MockLLMProvider,
    PluginRegistry,
    TransformNode,
    WorkflowNode,
    WorkflowStatus,
)
from generative_ai_workflow.workflow import NodeContext, NodeResult, NodeStatus


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    PluginRegistry.clear()
    mock = MockLLMProvider(responses={"default": "Node test response."})
    PluginRegistry.register_provider("mock", mock)
    yield


def make_context(input_data: dict, previous_outputs: dict | None = None) -> NodeContext:
    return NodeContext(
        workflow_id="wf-test",
        step_id="step-test",
        correlation_id="corr-test",
        input_data=input_data,
        previous_outputs=previous_outputs or {},
    )


class TestWorkflowNodeABC:
    """Tests for the WorkflowNode abstract base class."""

    def test_cannot_instantiate_abstract_node(self) -> None:
        with pytest.raises(TypeError):
            WorkflowNode(name="abstract")  # type: ignore[abstract]

    def test_concrete_subclass_requires_execute_async(self) -> None:
        class IncompleteNode(WorkflowNode):
            pass

        with pytest.raises(TypeError):
            IncompleteNode(name="incomplete")  # type: ignore[abstract]

    def test_concrete_subclass_works(self) -> None:
        class ConcreteNode(WorkflowNode):
            async def execute_async(self, context: NodeContext) -> NodeResult:
                return NodeResult(
                    step_id=context.step_id,
                    status=NodeStatus.COMPLETED,
                    output={"ok": True},
                    error=None,
                    duration_ms=0.0,
                )

        node = ConcreteNode(name="concrete")
        assert node.name == "concrete"
        assert node.is_critical is True

    def test_is_critical_defaults_to_true(self) -> None:
        class MinimalNode(WorkflowNode):
            async def execute_async(self, context: NodeContext) -> NodeResult:
                return NodeResult(
                    step_id=context.step_id,
                    status=NodeStatus.COMPLETED,
                    output={},
                    error=None,
                    duration_ms=0.0,
                )

        node = MinimalNode(name="minimal")
        assert node.is_critical is True

    def test_is_critical_can_be_set_false(self) -> None:
        class MinimalNode(WorkflowNode):
            async def execute_async(self, context: NodeContext) -> NodeResult:
                return NodeResult(
                    step_id=context.step_id,
                    status=NodeStatus.COMPLETED,
                    output={},
                    error=None,
                    duration_ms=0.0,
                )

        node = MinimalNode(name="optional", is_critical=False)
        assert node.is_critical is False

    def test_empty_name_raises(self) -> None:
        class MinimalNode(WorkflowNode):
            async def execute_async(self, context: NodeContext) -> NodeResult:
                return NodeResult(
                    step_id=context.step_id,
                    status=NodeStatus.COMPLETED,
                    output={},
                    error=None,
                    duration_ms=0.0,
                )

        with pytest.raises(ValueError):
            MinimalNode(name="")


class TestLLMNode:
    """Tests for LLMNode initialization and execution."""

    def test_requires_non_empty_prompt(self) -> None:
        with pytest.raises(ValueError, match="non-empty prompt"):
            LLMNode(name="gen", prompt="")

    def test_requires_non_empty_name(self) -> None:
        with pytest.raises(ValueError):
            LLMNode(name="", prompt="hello")

    def test_stores_prompt_template(self) -> None:
        node = LLMNode(name="gen", prompt="Hello {name}")
        assert node.prompt_template == "Hello {name}"

    def test_stores_provider_name(self) -> None:
        node = LLMNode(name="gen", prompt="hello", provider="mock")
        assert node.provider_name == "mock"

    def test_provider_name_defaults_to_none(self) -> None:
        node = LLMNode(name="gen", prompt="hello")
        assert node.provider_name is None

    async def test_execute_returns_llm_response(self) -> None:
        node = LLMNode(name="gen", prompt="Say hello", provider="mock")
        ctx = make_context({})
        result = await node.execute_async(ctx)
        assert result.status == NodeStatus.COMPLETED
        assert result.output is not None
        assert "llm_response" in result.output

    async def test_execute_substitutes_variables(self) -> None:
        node = LLMNode(name="gen", prompt="Hello {name}", provider="mock")
        ctx = make_context({"name": "World"})
        result = await node.execute_async(ctx)
        assert result.status == NodeStatus.COMPLETED

    async def test_execute_fails_on_missing_variable(self) -> None:
        node = LLMNode(name="gen", prompt="Hello {missing}", provider="mock")
        ctx = make_context({})
        result = await node.execute_async(ctx)
        assert result.status == NodeStatus.FAILED
        assert "missing" in result.error

    async def test_execute_uses_previous_outputs(self) -> None:
        node = LLMNode(name="gen", prompt="Value: {val}", provider="mock")
        ctx = make_context({}, previous_outputs={"val": "42"})
        result = await node.execute_async(ctx)
        assert result.status == NodeStatus.COMPLETED

    async def test_execute_records_token_usage(self) -> None:
        node = LLMNode(name="gen", prompt="hello", provider="mock")
        ctx = make_context({})
        result = await node.execute_async(ctx)
        assert result.token_usage is not None
        assert result.token_usage.total_tokens > 0

    async def test_execute_records_duration(self) -> None:
        node = LLMNode(name="gen", prompt="hello", provider="mock")
        ctx = make_context({})
        result = await node.execute_async(ctx)
        assert result.duration_ms >= 0.0


class TestTransformNode:
    """Tests for TransformNode initialization and execution."""

    def test_requires_non_empty_name(self) -> None:
        with pytest.raises(ValueError):
            TransformNode(name="", transform=lambda d: d)

    def test_stores_transform_callable(self) -> None:
        fn = lambda d: {"x": 1}
        node = TransformNode(name="t", transform=fn)
        assert node.transform is fn

    async def test_execute_applies_transform(self) -> None:
        node = TransformNode(name="double", transform=lambda d: {"result": d["value"] * 2})
        ctx = make_context({"value": 21})
        result = await node.execute_async(ctx)
        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"result": 42}

    async def test_execute_merges_input_and_previous(self) -> None:
        node = TransformNode(
            name="merge",
            transform=lambda d: {"combined": f"{d['a']}-{d['b']}"},
        )
        ctx = make_context({"a": "hello"}, previous_outputs={"b": "world"})
        result = await node.execute_async(ctx)
        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"combined": "hello-world"}

    async def test_execute_fails_gracefully_on_exception(self) -> None:
        def bad_transform(d: dict) -> dict:
            raise ValueError("intentional failure")

        node = TransformNode(name="bad", transform=bad_transform)
        ctx = make_context({})
        result = await node.execute_async(ctx)
        assert result.status == NodeStatus.FAILED
        assert "intentional failure" in result.error

    async def test_execute_records_duration(self) -> None:
        node = TransformNode(name="t", transform=lambda d: {})
        ctx = make_context({})
        result = await node.execute_async(ctx)
        assert result.duration_ms >= 0.0

    async def test_no_token_usage_for_transform(self) -> None:
        node = TransformNode(name="t", transform=lambda d: {})
        ctx = make_context({})
        result = await node.execute_async(ctx)
        assert result.token_usage is None
