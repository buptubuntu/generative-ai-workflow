"""
Unit tests for control flow primitives (ConditionalNode, ForEachNode, SwitchNode).

Tests verify:
- ConditionalNode initialization and validation
- Conditional branch execution (true/false paths)
- Error handling for condition evaluation failures
- Critical and non-critical child node failure handling
- Token usage aggregation across branch nodes
"""

import pytest
from unittest.mock import AsyncMock, Mock

from generative_ai_workflow.control_flow import (
    ConditionalNode,
    ExpressionError,
)
from generative_ai_workflow.workflow import NodeContext, NodeResult, NodeStatus
from generative_ai_workflow.providers.base import TokenUsage


# =============================================================================
# Test Helpers
# =============================================================================


def make_mock_node(name: str, output: dict, status: NodeStatus = NodeStatus.COMPLETED, is_critical: bool = True):
    """Create a mock WorkflowNode that returns specified output."""
    mock_node = Mock()
    mock_node.name = name
    mock_node.is_critical = is_critical
    mock_node.execute_async = AsyncMock(
        return_value=NodeResult(
            step_id="test-node-id",
            status=status,
            output=output,
            error=None if status == NodeStatus.COMPLETED else f"{name} failed",
            duration_ms=10.0,
            token_usage=None,
        )
    )
    return mock_node


def make_context(input_data: dict, previous_outputs: dict | None = None) -> NodeContext:
    """Create a NodeContext for testing."""
    return NodeContext(
        workflow_id="test-workflow",
        step_id="test-node",
        correlation_id="test-correlation",
        input_data=input_data,
        previous_outputs=previous_outputs or {},
    )


# =============================================================================
# ConditionalNode Unit Tests
# =============================================================================


class TestConditionalNodeInit:
    """Test ConditionalNode.__init__() validation (T017)."""

    def test_requires_non_empty_name(self) -> None:
        """Test that ConditionalNode requires a non-empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            ConditionalNode(
                name="",
                condition="x > 10",
                true_nodes=[make_mock_node("node1", {"result": 1})],
            )

    def test_requires_non_empty_condition(self) -> None:
        """Test that ConditionalNode requires a non-empty condition."""
        with pytest.raises(ValueError, match="condition cannot be empty"):
            ConditionalNode(
                name="test",
                condition="",
                true_nodes=[make_mock_node("node1", {"result": 1})],
            )

    def test_validates_condition_syntax(self) -> None:
        """Test that ConditionalNode validates condition syntax at init time."""
        with pytest.raises(ExpressionError, match="Invalid expression syntax"):
            ConditionalNode(
                name="test",
                condition="if x > 10:",
                true_nodes=[make_mock_node("node1", {"result": 1})],
            )

    def test_requires_at_least_one_true_node(self) -> None:
        """Test that ConditionalNode requires at least one true_node."""
        with pytest.raises(ValueError, match="at least one true_node"):
            ConditionalNode(
                name="test",
                condition="x > 10",
                true_nodes=[],
            )

    def test_false_nodes_optional(self) -> None:
        """Test that false_nodes is optional (defaults to empty list)."""
        node = ConditionalNode(
            name="test",
            condition="x > 10",
            true_nodes=[make_mock_node("node1", {"result": 1})],
        )
        assert node.false_nodes == []

    def test_successful_init(self) -> None:
        """Test successful ConditionalNode initialization."""
        true_node = make_mock_node("true_node", {"result": 1})
        false_node = make_mock_node("false_node", {"result": 2})

        node = ConditionalNode(
            name="test_conditional",
            condition="x > 10",
            true_nodes=[true_node],
            false_nodes=[false_node],
            is_critical=True,
        )

        assert node.name == "test_conditional"
        assert node.condition == "x > 10"
        assert node.true_nodes == [true_node]
        assert node.false_nodes == [false_node]
        assert node.is_critical is True


class TestConditionalNodeTrueBranch:
    """Test ConditionalNode with true branch execution (T018)."""

    @pytest.mark.asyncio
    async def test_executes_true_branch_when_condition_true(self) -> None:
        """Test that true branch executes when condition evaluates to True."""
        true_node = make_mock_node("true_node", {"result": "true_value"})
        false_node = make_mock_node("false_node", {"result": "false_value"})

        conditional = ConditionalNode(
            name="test",
            condition="x > 10",
            true_nodes=[true_node],
            false_nodes=[false_node],
        )

        context = make_context({"x": 42})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"result": "true_value"}
        true_node.execute_async.assert_awaited_once()
        false_node.execute_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_accumulates_output_from_multiple_true_nodes(self) -> None:
        """Test that output is accumulated from multiple nodes in true branch."""
        node1 = make_mock_node("node1", {"a": 1})
        node2 = make_mock_node("node2", {"b": 2})
        node3 = make_mock_node("node3", {"c": 3})

        conditional = ConditionalNode(
            name="test",
            condition="active == True",
            true_nodes=[node1, node2, node3],
        )

        context = make_context({"active": True})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"a": 1, "b": 2, "c": 3}


class TestConditionalNodeFalseBranch:
    """Test ConditionalNode with false branch execution (T019)."""

    @pytest.mark.asyncio
    async def test_executes_false_branch_when_condition_false(self) -> None:
        """Test that false branch executes when condition evaluates to False."""
        true_node = make_mock_node("true_node", {"result": "true_value"})
        false_node = make_mock_node("false_node", {"result": "false_value"})

        conditional = ConditionalNode(
            name="test",
            condition="x > 10",
            true_nodes=[true_node],
            false_nodes=[false_node],
        )

        context = make_context({"x": 5})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"result": "false_value"}
        true_node.execute_async.assert_not_awaited()
        false_node.execute_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_accumulates_output_from_multiple_false_nodes(self) -> None:
        """Test that output is accumulated from multiple nodes in false branch."""
        node1 = make_mock_node("node1", {"x": 10})
        node2 = make_mock_node("node2", {"y": 20})

        conditional = ConditionalNode(
            name="test",
            condition="status == 'active'",
            true_nodes=[make_mock_node("unused", {})],
            false_nodes=[node1, node2],
        )

        context = make_context({"status": "inactive"})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"x": 10, "y": 20}


class TestConditionalNodeNoFalseBranch:
    """Test ConditionalNode with no false_nodes (empty else branch) (T020)."""

    @pytest.mark.asyncio
    async def test_returns_empty_output_when_no_false_branch(self) -> None:
        """Test that empty output is returned when condition is false and no false_nodes."""
        true_node = make_mock_node("true_node", {"result": "value"})

        conditional = ConditionalNode(
            name="test",
            condition="x > 10",
            true_nodes=[true_node],
            false_nodes=[],  # No else branch
        )

        context = make_context({"x": 5})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {}
        true_node.execute_async.assert_not_awaited()


class TestConditionalNodeComplexExpressions:
    """Test ConditionalNode with complex boolean expressions (T021)."""

    @pytest.mark.asyncio
    async def test_and_operator(self) -> None:
        """Test condition with 'and' operator."""
        true_node = make_mock_node("true_node", {"result": "matched"})

        conditional = ConditionalNode(
            name="test",
            condition="x > 10 and y < 100",
            true_nodes=[true_node],
        )

        context = make_context({"x": 50, "y": 20})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"result": "matched"}

    @pytest.mark.asyncio
    async def test_or_operator(self) -> None:
        """Test condition with 'or' operator."""
        true_node = make_mock_node("true_node", {"result": "matched"})

        conditional = ConditionalNode(
            name="test",
            condition="priority > 8 or status == 'urgent'",
            true_nodes=[true_node],
        )

        context = make_context({"priority": 5, "status": "urgent"})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"result": "matched"}

    @pytest.mark.asyncio
    async def test_not_operator(self) -> None:
        """Test condition with 'not' operator."""
        true_node = make_mock_node("true_node", {"result": "matched"})

        conditional = ConditionalNode(
            name="test",
            condition="not disabled",
            true_nodes=[true_node],
        )

        context = make_context({"disabled": False})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"result": "matched"}

    @pytest.mark.asyncio
    async def test_in_operator(self) -> None:
        """Test condition with 'in' operator."""
        true_node = make_mock_node("true_node", {"result": "matched"})

        conditional = ConditionalNode(
            name="test",
            condition="type in ['email', 'sms', 'push']",
            true_nodes=[true_node],
        )

        context = make_context({"type": "sms"})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"result": "matched"}


class TestConditionalNodeErrorHandling:
    """Test ConditionalNode error handling (T022)."""

    @pytest.mark.asyncio
    async def test_condition_evaluation_failure_undefined_variable(self) -> None:
        """Test that undefined variable in condition causes node failure."""
        true_node = make_mock_node("true_node", {"result": 1})

        conditional = ConditionalNode(
            name="test",
            condition="missing_var > 10",
            true_nodes=[true_node],
        )

        context = make_context({"x": 5})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.FAILED
        assert "Condition evaluation failed" in result.error
        assert "missing_var" in result.error

    @pytest.mark.asyncio
    async def test_condition_evaluation_type_mismatch(self) -> None:
        """Test that type mismatch in condition causes node failure."""
        true_node = make_mock_node("true_node", {"result": 1})

        conditional = ConditionalNode(
            name="test",
            condition="x > 'string'",
            true_nodes=[true_node],
        )

        context = make_context({"x": 5})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.FAILED
        assert "Condition evaluation failed" in result.error or "Expression evaluation error" in result.error


class TestConditionalNodeCriticalChildFailure:
    """Test ConditionalNode with critical child node failure (T023)."""

    @pytest.mark.asyncio
    async def test_critical_child_failure_aborts_execution(self) -> None:
        """Test that critical child node failure aborts branch execution."""
        node1 = make_mock_node("node1", {"a": 1})
        failing_node = make_mock_node("failing", {}, status=NodeStatus.FAILED, is_critical=True)
        node3 = make_mock_node("node3", {"c": 3})

        conditional = ConditionalNode(
            name="test",
            condition="x > 10",
            true_nodes=[node1, failing_node, node3],
        )

        context = make_context({"x": 42})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.FAILED
        assert "Critical child node 'failing' failed" in result.error
        node1.execute_async.assert_awaited_once()
        failing_node.execute_async.assert_awaited_once()
        node3.execute_async.assert_not_awaited()  # Should not execute after failure


class TestConditionalNodeNonCriticalChildFailure:
    """Test ConditionalNode with non-critical child node failure (T024)."""

    @pytest.mark.asyncio
    async def test_non_critical_child_failure_continues_execution(self) -> None:
        """Test that non-critical child node failure does not abort execution."""
        node1 = make_mock_node("node1", {"a": 1})
        failing_node = make_mock_node("failing", {}, status=NodeStatus.FAILED, is_critical=False)
        node3 = make_mock_node("node3", {"c": 3})

        conditional = ConditionalNode(
            name="test",
            condition="x > 10",
            true_nodes=[node1, failing_node, node3],
        )

        context = make_context({"x": 42})
        result = await conditional.execute_async(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.output == {"a": 1, "c": 3}  # Output from node1 and node3
        node1.execute_async.assert_awaited_once()
        failing_node.execute_async.assert_awaited_once()
        node3.execute_async.assert_awaited_once()  # Should execute after non-critical failure
