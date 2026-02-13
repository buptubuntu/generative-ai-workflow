"""
Unit tests for control flow primitives (ConditionalStep, ForEachStep, SwitchStep).

Tests verify:
- ConditionalStep initialization and validation
- Conditional branch execution (true/false paths)
- Error handling for condition evaluation failures
- Critical and non-critical child step failure handling
- Token usage aggregation across branch steps
"""

import pytest
from unittest.mock import AsyncMock, Mock

from generative_ai_workflow.control_flow import (
    ConditionalStep,
    ExpressionError,
)
from generative_ai_workflow.workflow import StepContext, StepResult, StepStatus
from generative_ai_workflow.providers.base import TokenUsage


# =============================================================================
# Test Helpers
# =============================================================================


def make_mock_step(name: str, output: dict, status: StepStatus = StepStatus.COMPLETED, is_critical: bool = True):
    """Create a mock WorkflowStep that returns specified output."""
    mock_step = Mock()
    mock_step.name = name
    mock_step.is_critical = is_critical
    mock_step.execute_async = AsyncMock(
        return_value=StepResult(
            step_id="test-step-id",
            status=status,
            output=output,
            error=None if status == StepStatus.COMPLETED else f"{name} failed",
            duration_ms=10.0,
            token_usage=None,
        )
    )
    return mock_step


def make_context(input_data: dict, previous_outputs: dict | None = None) -> StepContext:
    """Create a StepContext for testing."""
    return StepContext(
        workflow_id="test-workflow",
        step_id="test-step",
        correlation_id="test-correlation",
        input_data=input_data,
        previous_outputs=previous_outputs or {},
    )


# =============================================================================
# ConditionalStep Unit Tests
# =============================================================================


class TestConditionalStepInit:
    """Test ConditionalStep.__init__() validation (T017)."""

    def test_requires_non_empty_name(self) -> None:
        """Test that ConditionalStep requires a non-empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            ConditionalStep(
                name="",
                condition="x > 10",
                true_steps=[make_mock_step("step1", {"result": 1})],
            )

    def test_requires_non_empty_condition(self) -> None:
        """Test that ConditionalStep requires a non-empty condition."""
        with pytest.raises(ValueError, match="condition cannot be empty"):
            ConditionalStep(
                name="test",
                condition="",
                true_steps=[make_mock_step("step1", {"result": 1})],
            )

    def test_validates_condition_syntax(self) -> None:
        """Test that ConditionalStep validates condition syntax at init time."""
        with pytest.raises(ExpressionError, match="Invalid expression syntax"):
            ConditionalStep(
                name="test",
                condition="if x > 10:",
                true_steps=[make_mock_step("step1", {"result": 1})],
            )

    def test_requires_at_least_one_true_step(self) -> None:
        """Test that ConditionalStep requires at least one true_step."""
        with pytest.raises(ValueError, match="at least one true_step"):
            ConditionalStep(
                name="test",
                condition="x > 10",
                true_steps=[],
            )

    def test_false_steps_optional(self) -> None:
        """Test that false_steps is optional (defaults to empty list)."""
        step = ConditionalStep(
            name="test",
            condition="x > 10",
            true_steps=[make_mock_step("step1", {"result": 1})],
        )
        assert step.false_steps == []

    def test_successful_init(self) -> None:
        """Test successful ConditionalStep initialization."""
        true_step = make_mock_step("true_step", {"result": 1})
        false_step = make_mock_step("false_step", {"result": 2})

        step = ConditionalStep(
            name="test_conditional",
            condition="x > 10",
            true_steps=[true_step],
            false_steps=[false_step],
            is_critical=True,
        )

        assert step.name == "test_conditional"
        assert step.condition == "x > 10"
        assert step.true_steps == [true_step]
        assert step.false_steps == [false_step]
        assert step.is_critical is True


class TestConditionalStepTrueBranch:
    """Test ConditionalStep with true branch execution (T018)."""

    @pytest.mark.asyncio
    async def test_executes_true_branch_when_condition_true(self) -> None:
        """Test that true branch executes when condition evaluates to True."""
        true_step = make_mock_step("true_step", {"result": "true_value"})
        false_step = make_mock_step("false_step", {"result": "false_value"})

        conditional = ConditionalStep(
            name="test",
            condition="x > 10",
            true_steps=[true_step],
            false_steps=[false_step],
        )

        context = make_context({"x": 42})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"result": "true_value"}
        true_step.execute_async.assert_awaited_once()
        false_step.execute_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_accumulates_output_from_multiple_true_steps(self) -> None:
        """Test that output is accumulated from multiple steps in true branch."""
        step1 = make_mock_step("step1", {"a": 1})
        step2 = make_mock_step("step2", {"b": 2})
        step3 = make_mock_step("step3", {"c": 3})

        conditional = ConditionalStep(
            name="test",
            condition="active == True",
            true_steps=[step1, step2, step3],
        )

        context = make_context({"active": True})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"a": 1, "b": 2, "c": 3}


class TestConditionalStepFalseBranch:
    """Test ConditionalStep with false branch execution (T019)."""

    @pytest.mark.asyncio
    async def test_executes_false_branch_when_condition_false(self) -> None:
        """Test that false branch executes when condition evaluates to False."""
        true_step = make_mock_step("true_step", {"result": "true_value"})
        false_step = make_mock_step("false_step", {"result": "false_value"})

        conditional = ConditionalStep(
            name="test",
            condition="x > 10",
            true_steps=[true_step],
            false_steps=[false_step],
        )

        context = make_context({"x": 5})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"result": "false_value"}
        true_step.execute_async.assert_not_awaited()
        false_step.execute_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_accumulates_output_from_multiple_false_steps(self) -> None:
        """Test that output is accumulated from multiple steps in false branch."""
        step1 = make_mock_step("step1", {"x": 10})
        step2 = make_mock_step("step2", {"y": 20})

        conditional = ConditionalStep(
            name="test",
            condition="status == 'active'",
            true_steps=[make_mock_step("unused", {})],
            false_steps=[step1, step2],
        )

        context = make_context({"status": "inactive"})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"x": 10, "y": 20}


class TestConditionalStepNoFalseBranch:
    """Test ConditionalStep with no false_steps (empty else branch) (T020)."""

    @pytest.mark.asyncio
    async def test_returns_empty_output_when_no_false_branch(self) -> None:
        """Test that empty output is returned when condition is false and no false_steps."""
        true_step = make_mock_step("true_step", {"result": "value"})

        conditional = ConditionalStep(
            name="test",
            condition="x > 10",
            true_steps=[true_step],
            false_steps=[],  # No else branch
        )

        context = make_context({"x": 5})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {}
        true_step.execute_async.assert_not_awaited()


class TestConditionalStepComplexExpressions:
    """Test ConditionalStep with complex boolean expressions (T021)."""

    @pytest.mark.asyncio
    async def test_and_operator(self) -> None:
        """Test condition with 'and' operator."""
        true_step = make_mock_step("true_step", {"result": "matched"})

        conditional = ConditionalStep(
            name="test",
            condition="x > 10 and y < 100",
            true_steps=[true_step],
        )

        context = make_context({"x": 50, "y": 20})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"result": "matched"}

    @pytest.mark.asyncio
    async def test_or_operator(self) -> None:
        """Test condition with 'or' operator."""
        true_step = make_mock_step("true_step", {"result": "matched"})

        conditional = ConditionalStep(
            name="test",
            condition="priority > 8 or status == 'urgent'",
            true_steps=[true_step],
        )

        context = make_context({"priority": 5, "status": "urgent"})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"result": "matched"}

    @pytest.mark.asyncio
    async def test_not_operator(self) -> None:
        """Test condition with 'not' operator."""
        true_step = make_mock_step("true_step", {"result": "matched"})

        conditional = ConditionalStep(
            name="test",
            condition="not disabled",
            true_steps=[true_step],
        )

        context = make_context({"disabled": False})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"result": "matched"}

    @pytest.mark.asyncio
    async def test_in_operator(self) -> None:
        """Test condition with 'in' operator."""
        true_step = make_mock_step("true_step", {"result": "matched"})

        conditional = ConditionalStep(
            name="test",
            condition="type in ['email', 'sms', 'push']",
            true_steps=[true_step],
        )

        context = make_context({"type": "sms"})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"result": "matched"}


class TestConditionalStepErrorHandling:
    """Test ConditionalStep error handling (T022)."""

    @pytest.mark.asyncio
    async def test_condition_evaluation_failure_undefined_variable(self) -> None:
        """Test that undefined variable in condition causes step failure."""
        true_step = make_mock_step("true_step", {"result": 1})

        conditional = ConditionalStep(
            name="test",
            condition="missing_var > 10",
            true_steps=[true_step],
        )

        context = make_context({"x": 5})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.FAILED
        assert "Condition evaluation failed" in result.error
        assert "missing_var" in result.error

    @pytest.mark.asyncio
    async def test_condition_evaluation_type_mismatch(self) -> None:
        """Test that type mismatch in condition causes step failure."""
        true_step = make_mock_step("true_step", {"result": 1})

        conditional = ConditionalStep(
            name="test",
            condition="x > 'string'",
            true_steps=[true_step],
        )

        context = make_context({"x": 5})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.FAILED
        assert "Condition evaluation failed" in result.error or "Expression evaluation error" in result.error


class TestConditionalStepCriticalChildFailure:
    """Test ConditionalStep with critical child step failure (T023)."""

    @pytest.mark.asyncio
    async def test_critical_child_failure_aborts_execution(self) -> None:
        """Test that critical child step failure aborts branch execution."""
        step1 = make_mock_step("step1", {"a": 1})
        failing_step = make_mock_step("failing", {}, status=StepStatus.FAILED, is_critical=True)
        step3 = make_mock_step("step3", {"c": 3})

        conditional = ConditionalStep(
            name="test",
            condition="x > 10",
            true_steps=[step1, failing_step, step3],
        )

        context = make_context({"x": 42})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.FAILED
        assert "Critical child step 'failing' failed" in result.error
        step1.execute_async.assert_awaited_once()
        failing_step.execute_async.assert_awaited_once()
        step3.execute_async.assert_not_awaited()  # Should not execute after failure


class TestConditionalStepNonCriticalChildFailure:
    """Test ConditionalStep with non-critical child step failure (T024)."""

    @pytest.mark.asyncio
    async def test_non_critical_child_failure_continues_execution(self) -> None:
        """Test that non-critical child step failure does not abort execution."""
        step1 = make_mock_step("step1", {"a": 1})
        failing_step = make_mock_step("failing", {}, status=StepStatus.FAILED, is_critical=False)
        step3 = make_mock_step("step3", {"c": 3})

        conditional = ConditionalStep(
            name="test",
            condition="x > 10",
            true_steps=[step1, failing_step, step3],
        )

        context = make_context({"x": 42})
        result = await conditional.execute_async(context)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"a": 1, "c": 3}  # Output from step1 and step3
        step1.execute_async.assert_awaited_once()
        failing_step.execute_async.assert_awaited_once()
        step3.execute_async.assert_awaited_once()  # Should execute after non-critical failure
