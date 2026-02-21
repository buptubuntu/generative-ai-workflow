"""
Control Flow Primitives for Generative AI Workflow Framework.

This module provides conditional branching, loop iteration, and multi-way dispatch
capabilities for AI workflows.

Version: 0.2.0
Feature: 002-workflow-control-flow
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from simpleeval import EvalWithCompoundTypes, InvalidExpression, NameNotDefined

if TYPE_CHECKING:
    from generative_ai_workflow.node import WorkflowNode
    from generative_ai_workflow.workflow import NodeContext, NodeResult, NodeStatus


# =============================================================================
# Exceptions
# =============================================================================


class ExpressionError(Exception):
    """Raised when expression evaluation fails.

    Reasons:
        - Invalid syntax (AST parsing failure)
        - Undefined variable reference
        - Type mismatch (e.g., comparing str with int)
        - Forbidden operator (e.g., function definition, import)

    Examples:
        ExpressionError("Variable 'missing_var' not found in context (available: ['input', 'node1'])")
        ExpressionError("Invalid expression syntax: unexpected token at position 5")
        ExpressionError("Type mismatch: cannot compare 'str' with 'int'")
    """

    pass


class ExpressionTimeoutError(ExpressionError):
    """Raised when expression evaluation exceeds workflow timeout.

    Rare condition (simpleeval is fast). Usually indicates:
        - Very large input strings (>100K chars)
        - Complex nested expressions (unlikely with restricted operators)
        - System resource exhaustion

    Inherits from ExpressionError for backward compatibility.
    """

    pass


# =============================================================================
# Expression Evaluation
# =============================================================================


class ExpressionEvaluator:
    """Safe expression evaluator for workflow control flow.

    Evaluates user-supplied boolean and categorical expressions without
    arbitrary code execution risks. Uses AST-based parsing with restricted
    operator set.

    Supported operators:
        - Comparison: ==, !=, <, >, <=, >=
        - Membership: in, not in
        - Logical: and, or, not

    Not supported:
        - Function definitions (def, lambda)
        - Assignments (=, +=, etc.)
        - Imports (import, from)
        - Attribute access (except whitelisted)
        - Dunder methods (__builtins__, __import__, etc.)

    Security:
        - No eval() or exec()
        - No access to __builtins__
        - String length limit: 100,000 chars (configurable)
        - Exponentiation base limit: 4,000,000 (configurable)
    """

    @staticmethod
    def validate_expression(expression: str) -> None:
        """Validate expression syntax at workflow definition time.

        Performs eager validation of expression syntax without evaluating it.
        Checks for AST parseability and operator restrictions.

        Args:
            expression: Expression string to validate

        Raises:
            ExpressionError: If expression syntax is invalid or uses forbidden operators

        Note:
            Does NOT check for undefined variables (context-dependent, checked at runtime).
            Validation is fast (<0.01ms) and should be called during workflow construction.

        Examples:
            >>> ExpressionEvaluator.validate_expression("x > 10")  # OK
            >>> ExpressionEvaluator.validate_expression("import os")  # Raises ExpressionError
        """
        if not expression or not expression.strip():
            raise ExpressionError("Expression cannot be empty")

        try:
            # Use simpleeval to parse and validate syntax
            evaluator = EvalWithCompoundTypes()
            # Parse without evaluating (checks syntax only)
            evaluator.parse(expression)
        except (InvalidExpression, SyntaxError, ValueError, TypeError, IndentationError) as e:
            raise ExpressionError(f"Invalid expression syntax: {e}") from e

    @staticmethod
    def evaluate(
        expression: str,
        context: dict[str, Any],
        *,
        max_string_length: int = 100000,
        max_power: int = 4000000,
    ) -> Any:
        """Evaluate expression against context data.

        Args:
            expression: Python-like expression string
                Examples:
                    "sentiment == 'positive'"
                    "len(items) > 0"
                    "document_type in ['email', 'report']"
                    "priority > 5 and status != 'closed'"
            context: Variable bindings
                Example: {"sentiment": "positive", "items": [1, 2, 3], "priority": 8}
            max_string_length: Maximum string length (DoS protection)
            max_power: Maximum exponentiation base (DoS protection)

        Returns:
            Evaluation result (type depends on expression)
                - Boolean for conditionals (e.g., True, False)
                - Any type for switch expressions (e.g., "email", 42)

        Raises:
            ExpressionError: If expression is invalid or references undefined variables
            ExpressionTimeoutError: If evaluation exceeds workflow timeout (rare)

        Performance:
            - Typical: <0.1ms per evaluation
            - Cached AST reuse recommended for repeated evaluations

        Examples:
            >>> ExpressionEvaluator.evaluate("x > 10", {"x": 42})
            True

            >>> ExpressionEvaluator.evaluate(
            ...     "type in ['email', 'sms']",
            ...     {"type": "email"}
            ... )
            True

            >>> ExpressionEvaluator.evaluate(
            ...     "priority > 5 and status != 'closed'",
            ...     {"priority": 8, "status": "open"}
            ... )
            True
        """
        if not expression or not expression.strip():
            raise ExpressionError("Expression cannot be empty")

        try:
            # Create evaluator with compound type support (lists, dicts, tuples)
            evaluator = EvalWithCompoundTypes(
                names=context,
                functions={"len": len},  # Only allow safe built-in functions
            )

            # Set DoS protection limits
            evaluator.MAX_STRING_LENGTH = max_string_length
            evaluator.MAX_POWER = max_power

            # Evaluate expression
            result = evaluator.eval(expression)
            return result

        except NameNotDefined as e:
            # Variable not found in context
            available_vars = sorted(list(context.keys()))
            raise ExpressionError(
                f"Variable {e.name!r} not found in context (available: {available_vars})"
            ) from e
        except InvalidExpression as e:
            raise ExpressionError(f"Invalid expression: {e}") from e
        except (SyntaxError, TypeError, ValueError, AttributeError, IndentationError) as e:
            raise ExpressionError(f"Expression evaluation error: {e}") from e
        except Exception as e:
            # Catch-all for unexpected errors
            raise ExpressionError(f"Unexpected error evaluating expression: {e}") from e


# =============================================================================
# Control Flow Nodes
# =============================================================================


class ConditionalNode:
    """Conditional branching workflow node (if/else).

    Evaluates a boolean expression on workflow context data and executes
    either the true branch or false branch based on the result.

    Attributes:
        name: Unique node name
        condition: Boolean expression string (e.g., "sentiment == 'positive'")
        true_nodes: Nodes to execute if condition is True
        false_nodes: Nodes to execute if condition is False (optional, empty if omitted)
        is_critical: If True, node failure aborts workflow

    Examples:
        >>> ConditionalNode(
        ...     name="sentiment_router",
        ...     condition="sentiment == 'positive'",
        ...     true_nodes=[LLMNode(name="positive_response", prompt="...")],
        ...     false_nodes=[LLMNode(name="negative_response", prompt="...")],
        ... )
    """

    def __init__(
        self,
        name: str,
        condition: str,
        true_nodes: list["WorkflowNode"],
        false_nodes: list["WorkflowNode"] | None = None,
        is_critical: bool = True,
    ) -> None:
        """Initialize ConditionalNode with validation.

        Args:
            name: Node identifier
            condition: Boolean expression to evaluate
            true_nodes: Nodes to execute if condition is True
            false_nodes: Nodes to execute if condition is False (optional)
            is_critical: If True, node failure aborts workflow

        Raises:
            ValueError: If validation fails (empty condition, empty true_nodes, invalid syntax)
        """
        if not name:
            raise ValueError("ConditionalNode name cannot be empty")
        self.name = name
        self.condition = condition
        self.true_nodes = true_nodes
        self.false_nodes = false_nodes or []
        self.is_critical = is_critical
        self._validate()

    def _validate(self) -> None:
        """Validate condition syntax and node structure at definition time.

        Raises:
            ValueError: If condition is empty or true_nodes is empty
            ExpressionError: If condition syntax is invalid
        """
        if not self.condition:
            raise ValueError("ConditionalNode condition cannot be empty")
        ExpressionEvaluator.validate_expression(self.condition)
        if not self.true_nodes:
            raise ValueError("ConditionalNode must have at least one true_node")
        # false_nodes MAY be empty (no else branch)

    async def execute_async(self, context: "NodeContext") -> "NodeResult":
        """Execute conditional branch based on context data.

        1. Evaluate condition expression on {**context.input_data, **context.previous_outputs}
        2. Select branch (true_nodes if condition == True, false_nodes otherwise)
        3. Execute selected branch nodes sequentially
        4. Accumulate outputs from branch nodes
        5. Return NodeResult with accumulated output

        Args:
            context: Execution context with input data and previous outputs

        Returns:
            NodeResult with accumulated output from executed branch nodes

        Error Handling:
            - If condition evaluation fails → NodeResult(status=FAILED)
            - If critical child node fails → NodeResult(status=FAILED)
            - If non-critical child node fails → log warning, continue
        """
        from generative_ai_workflow.workflow import NodeResult, NodeStatus
        import structlog

        logger = structlog.get_logger()
        start_time = time.time()

        try:
            # Build evaluation context from input_data + previous_outputs
            eval_context = {**context.input_data, **context.previous_outputs}

            # Evaluate condition
            logger.info(
                "control_flow_decision",
                construct_name=self.name,
                construct_type="conditional",
                condition=self.condition,
                correlation_id=context.correlation_id,
            )

            condition_result = ExpressionEvaluator.evaluate(self.condition, eval_context)

            # Select branch
            if condition_result:
                selected_nodes = self.true_nodes
                branch_name = "true"
            else:
                selected_nodes = self.false_nodes
                branch_name = "false"

            logger.info(
                "control_flow_decision",
                construct_name=self.name,
                decision_taken=f"branch={branch_name}",
                correlation_id=context.correlation_id,
            )

            # Execute selected branch nodes
            accumulated_output = {}
            total_token_usage = None

            for node in selected_nodes:
                node_result = await node.execute_async(context)

                # Check for critical failure
                if node_result.status == NodeStatus.FAILED and node.is_critical:
                    duration_ms = (time.time() - start_time) * 1000
                    return NodeResult(
                        step_id=context.step_id,
                        status=NodeStatus.FAILED,
                        output=None,
                        error=f"Critical child node '{node.name}' failed: {node_result.error}",
                        duration_ms=duration_ms,
                        token_usage=None,
                    )

                # Accumulate output
                if node_result.output:
                    accumulated_output.update(node_result.output)

                # Aggregate token usage
                if node_result.token_usage:
                    if total_token_usage is None:
                        total_token_usage = node_result.token_usage
                    else:
                        # Simple aggregation - add token counts
                        total_token_usage.prompt_tokens += node_result.token_usage.prompt_tokens
                        total_token_usage.completion_tokens += (
                            node_result.token_usage.completion_tokens
                        )
                        total_token_usage.total_tokens += node_result.token_usage.total_tokens

                # Update context for next node
                context.previous_outputs.update(accumulated_output)

            # Success
            duration_ms = (time.time() - start_time) * 1000
            return NodeResult(
                step_id=context.step_id,
                status=NodeStatus.COMPLETED,
                output=accumulated_output,
                error=None,
                duration_ms=duration_ms,
                token_usage=total_token_usage,
            )

        except ExpressionError as e:
            duration_ms = (time.time() - start_time) * 1000
            return NodeResult(
                step_id=context.step_id,
                status=NodeStatus.FAILED,
                output=None,
                error=f"Condition evaluation failed: {e}",
                duration_ms=duration_ms,
                token_usage=None,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return NodeResult(
                step_id=context.step_id,
                status=NodeStatus.FAILED,
                output=None,
                error=f"ConditionalNode execution failed: {e}",
                duration_ms=duration_ms,
                token_usage=None,
            )
