"""
Unit tests for ExpressionEvaluator.

Tests verify:
- Expression validation (syntax checking)
- Safe expression evaluation
- Context variable resolution
- Error handling (undefined variables, invalid syntax)
- Security (no eval, no __builtins__ access)
"""

import pytest

from generative_ai_workflow.control_flow import ExpressionError, ExpressionEvaluator


class TestExpressionValidation:
    """Test ExpressionEvaluator.validate_expression()."""

    def test_validate_simple_expression(self) -> None:
        """Test validation of simple valid expressions."""
        ExpressionEvaluator.validate_expression("x > 10")
        ExpressionEvaluator.validate_expression("sentiment == 'positive'")
        ExpressionEvaluator.validate_expression("len(items) > 0")

    def test_validate_complex_expression(self) -> None:
        """Test validation of complex boolean expressions."""
        ExpressionEvaluator.validate_expression("x > 5 and y < 10")
        ExpressionEvaluator.validate_expression("priority > 8 or status == 'urgent'")
        ExpressionEvaluator.validate_expression("type in ['email', 'sms'] and active")

    def test_validate_empty_expression_raises_error(self) -> None:
        """Test that empty expressions raise ExpressionError."""
        with pytest.raises(ExpressionError, match="cannot be empty"):
            ExpressionEvaluator.validate_expression("")

        with pytest.raises(ExpressionError, match="cannot be empty"):
            ExpressionEvaluator.validate_expression("   ")

    def test_validate_invalid_syntax_raises_error(self) -> None:
        """Test that invalid syntax raises ExpressionError."""
        with pytest.raises(ExpressionError, match="syntax|Invalid"):
            ExpressionEvaluator.validate_expression("x + * 10")

        with pytest.raises(ExpressionError, match="syntax|Invalid"):
            ExpressionEvaluator.validate_expression("if x > 10:")


class TestExpressionEvaluation:
    """Test ExpressionEvaluator.evaluate() with valid expressions."""

    def test_evaluate_comparison_operators(self) -> None:
        """Test evaluation of comparison operators."""
        assert ExpressionEvaluator.evaluate("x > 10", {"x": 42}) is True
        assert ExpressionEvaluator.evaluate("x > 10", {"x": 5}) is False
        assert ExpressionEvaluator.evaluate("x == 10", {"x": 10}) is True
        assert ExpressionEvaluator.evaluate("x != 10", {"x": 5}) is True
        assert ExpressionEvaluator.evaluate("x <= 10", {"x": 10}) is True
        assert ExpressionEvaluator.evaluate("x >= 10", {"x": 15}) is True

    def test_evaluate_membership_operators(self) -> None:
        """Test evaluation of membership operators (in, not in)."""
        assert ExpressionEvaluator.evaluate("type in ['email', 'sms']", {"type": "email"}) is True
        assert (
            ExpressionEvaluator.evaluate("type in ['email', 'sms']", {"type": "report"}) is False
        )
        assert (
            ExpressionEvaluator.evaluate("status not in ['closed', 'archived']", {"status": "open"})
            is True
        )

    def test_evaluate_logical_operators(self) -> None:
        """Test evaluation of logical operators (and, or, not)."""
        context = {"x": 10, "y": 5, "active": True}
        assert ExpressionEvaluator.evaluate("x > 5 and y < 10", context) is True
        assert ExpressionEvaluator.evaluate("x > 15 or y < 10", context) is True
        assert ExpressionEvaluator.evaluate("not active", context) is False
        assert ExpressionEvaluator.evaluate("x > 5 and y < 10 and active", context) is True

    def test_evaluate_with_string_values(self) -> None:
        """Test evaluation with string context values."""
        context = {"sentiment": "positive", "status": "complete"}
        assert ExpressionEvaluator.evaluate("sentiment == 'positive'", context) is True
        assert ExpressionEvaluator.evaluate("status != 'pending'", context) is True

    def test_evaluate_with_len_function(self) -> None:
        """Test evaluation using len() function."""
        assert ExpressionEvaluator.evaluate("len(items) > 0", {"items": [1, 2, 3]}) is True
        assert ExpressionEvaluator.evaluate("len(items) == 0", {"items": []}) is True
        assert ExpressionEvaluator.evaluate("len(text) > 5", {"text": "hello world"}) is True

    def test_evaluate_returns_non_boolean_for_switch(self) -> None:
        """Test that evaluate can return non-boolean values for switch expressions."""
        assert ExpressionEvaluator.evaluate("document_type", {"document_type": "email"}) == "email"
        assert ExpressionEvaluator.evaluate("priority", {"priority": 8}) == 8
        assert ExpressionEvaluator.evaluate("len(items)", {"items": [1, 2, 3]}) == 3


class TestExpressionErrorHandling:
    """Test ExpressionEvaluator error handling."""

    def test_evaluate_undefined_variable_raises_error(self) -> None:
        """Test that undefined variables raise ExpressionError with available vars."""
        with pytest.raises(
            ExpressionError, match=r"Variable.*not found.*available.*\['x', 'y'\]"
        ):
            ExpressionEvaluator.evaluate("missing_var > 10", {"x": 5, "y": 10})

    def test_evaluate_empty_expression_raises_error(self) -> None:
        """Test that empty expressions raise ExpressionError."""
        with pytest.raises(ExpressionError, match="cannot be empty"):
            ExpressionEvaluator.evaluate("", {"x": 5})

    def test_evaluate_type_mismatch_raises_error(self) -> None:
        """Test that type mismatches raise ExpressionError."""
        with pytest.raises(ExpressionError, match="evaluation error|not supported"):
            ExpressionEvaluator.evaluate("x + 'string'", {"x": 10})

    def test_evaluate_invalid_syntax_raises_error(self) -> None:
        """Test that invalid syntax raises ExpressionError."""
        with pytest.raises(ExpressionError):
            ExpressionEvaluator.evaluate("x + * 10", {"x": 5})

    def test_evaluate_with_empty_context(self) -> None:
        """Test evaluation with empty context (literals only)."""
        assert ExpressionEvaluator.evaluate("5 > 3", {}) is True
        assert ExpressionEvaluator.evaluate("'hello' == 'hello'", {}) is True
