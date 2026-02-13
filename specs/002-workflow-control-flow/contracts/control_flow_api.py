"""
API Contract: Control Flow Primitives for Generative AI Workflow Framework

This file defines the public API contracts for control flow step types and expression evaluation.
All implementations must conform to these interfaces.

Version: 0.2.0 (002-workflow-control-flow)
Date: 2026-02-08
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from generative_ai_workflow import WorkflowStep, StepContext, StepResult


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
        ...

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
        ...


# =============================================================================
# Control Flow Steps
# =============================================================================

class ConditionalStep(WorkflowStep):
    """Conditional branching workflow step (if/else).

    Evaluates a boolean expression on workflow context data and executes
    either the true branch or false branch based on the result.

    Thread Safety:
        Not thread-safe. Designed for sequential async execution.

    Observability:
        Logs control flow decision: "ConditionalStep 'X' took true/false branch"

    Token Usage:
        Aggregates token usage from nested LLMStep calls in executed branch.

    Examples:
        >>> from generative_ai_workflow import ConditionalStep, LLMStep
        >>>
        >>> # Route based on sentiment analysis result
        >>> ConditionalStep(
        ...     name="sentiment_router",
        ...     condition="sentiment == 'positive'",
        ...     true_steps=[
        ...         LLMStep(name="positive_response", prompt="Generate positive reply: {text}"),
        ...     ],
        ...     false_steps=[
        ...         LLMStep(name="negative_response", prompt="Generate empathetic reply: {text}"),
        ...     ],
        ... )

        >>> # Conditional with no else branch (false_steps omitted)
        >>> ConditionalStep(
        ...     name="high_priority_only",
        ...     condition="priority > 8",
        ...     true_steps=[
        ...         LLMStep(name="escalate", prompt="Escalate: {issue}"),
        ...     ],
        ...     # false_steps defaults to [] (skip if condition false)
        ... )
    """

    condition: str
    """Boolean expression evaluated on context.

    Must evaluate to boolean (True/False). References workflow context variables.
    Validated at workflow definition time for syntax, evaluated at runtime.

    Examples:
        "sentiment == 'positive'"
        "confidence > 0.8"
        "error_count == 0 and status != 'failed'"
    """

    true_steps: list[WorkflowStep]
    """Steps executed if condition is True.

    Must contain at least one step. Executed sequentially in order.
    All steps must have unique names within branch.
    """

    false_steps: list[WorkflowStep]
    """Steps executed if condition is False.

    Optional (defaults to empty list). If omitted and condition is False,
    step returns immediately with empty output.
    """

    is_critical: bool
    """If True, step failure aborts workflow. If False, failure is logged and skipped.

    Inherited from WorkflowStep. Applies to this step's execution, not nested steps
    (nested steps have their own is_critical settings).
    """

    def __init__(
        self,
        name: str,
        condition: str,
        true_steps: list[WorkflowStep],
        false_steps: list[WorkflowStep] | None = None,
        is_critical: bool = True,
    ) -> None:
        """Initialize conditional step.

        Args:
            name: Unique step name (must be non-empty)
            condition: Boolean expression string
            true_steps: Steps for true branch (must be non-empty)
            false_steps: Steps for false branch (optional, defaults to [])
            is_critical: Whether failure aborts workflow (defaults to True)

        Raises:
            ValueError: If name is empty, condition is empty, true_steps is empty,
                        or condition has invalid syntax
        """
        ...

    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute conditional branch based on context data.

        Execution flow:
            1. Evaluate condition expression on {**context.input_data, **context.previous_outputs}
            2. Select branch (true_steps if condition == True, false_steps otherwise)
            3. Execute selected branch steps sequentially
            4. Accumulate outputs from branch steps
            5. Return StepResult with accumulated output

        Error Handling:
            - Condition evaluation fails → StepResult(status=FAILED, error="...")
            - Child step fails and is_critical → StepResult(status=FAILED, error="...")
            - Child step fails and not is_critical → log warning, continue

        Args:
            context: Execution context with input_data, previous_outputs, config

        Returns:
            StepResult with:
                - output: Accumulated output from executed branch steps
                - duration_ms: Total execution time (condition eval + branch execution)
                - token_usage: Aggregated from nested LLMStep calls (if any)
                - status: COMPLETED or FAILED

        Performance:
            - Condition evaluation: <0.1ms
            - Branch dispatch overhead: <0.2ms
            - Total overhead: ≤5% vs. equivalent plain steps (SC-007)
        """
        ...


class ForEachStep(WorkflowStep):
    """Loop iteration workflow step (for-each).

    Iterates over a list from workflow context and executes loop body steps
    for each item. Collects results from all iterations.

    Sequential Execution:
        Iterations execute sequentially (not parallel). Iteration N+1 sees
        context updates from iteration N.

    Limits:
        - Maximum iterations: Configurable (default 100, WorkflowConfig.max_iterations)
        - Maximum nesting depth: Configurable (default 5, WorkflowConfig.max_nesting_depth)

    Observability:
        Logs iteration count: "ForEachStep 'X' completed N iterations"
        Logs per-iteration errors with index: "Iteration 5: step 'Y' failed: ..."

    Token Usage:
        Aggregates token usage from all iterations' LLMStep calls.

    Examples:
        >>> from generative_ai_workflow import ForEachStep, LLMStep
        >>>
        >>> # Batch process documents
        >>> ForEachStep(
        ...     name="batch_summarizer",
        ...     items_var="documents",         # Read list from context
        ...     loop_var="doc",                # Current item name in loop
        ...     loop_steps=[
        ...         LLMStep(name="summarize", prompt="Summarize: {doc}"),
        ...     ],
        ...     output_var="summaries",        # Collected results
        ... )
        >>>
        >>> # Usage in workflow:
        >>> workflow = Workflow(
        ...     steps=[
        ...         TransformStep(name="load", transform=lambda _: {"documents": ["doc1", "doc2", "doc3"]}),
        ...         ForEachStep(
        ...             name="process",
        ...             items_var="documents",
        ...             loop_var="doc",
        ...             loop_steps=[LLMStep(name="analyze", prompt="Analyze: {doc}")],
        ...             output_var="results",
        ...         ),
        ...     ]
        ... )
        >>> result = workflow.execute({})
        >>> result.output["results"]  # ["analysis1", "analysis2", "analysis3"]
    """

    items_var: str
    """Variable name containing list to iterate over.

    Resolved from {**context.input_data, **context.previous_outputs}.
    Must reference a list (not dict, not string, not scalar).

    Example: "documents" → reads context.previous_outputs["documents"]
    """

    loop_var: str
    """Variable name for current item (available in loop body).

    Injected into nested step context.variables for each iteration.
    Loop body steps can reference it in templates via {loop_var}.

    Example: "doc" → loop body steps can use {doc} in prompts
    """

    loop_steps: list[WorkflowStep]
    """Steps executed for each item.

    Must contain at least one step. Executed sequentially for each iteration.
    All steps must have unique names.
    """

    output_var: str
    """Variable name for collected results.

    Results stored in output[output_var] as a list.
    Each element is the accumulated output from one iteration's loop_steps.

    Example: "summaries" → output["summaries"] = [iter1_out, iter2_out, ...]
    """

    max_iterations: int | None
    """Override WorkflowConfig.max_iterations (optional).

    If None, uses WorkflowConfig.max_iterations (default: 100).
    If specified, must be > 0.
    Prevents runaway loops (DoW protection).
    """

    is_critical: bool
    """If True, step failure aborts workflow. If False, failure is logged and skipped."""

    def __init__(
        self,
        name: str,
        items_var: str,
        loop_var: str,
        loop_steps: list[WorkflowStep],
        output_var: str,
        max_iterations: int | None = None,
        is_critical: bool = True,
    ) -> None:
        """Initialize for-each loop step.

        Args:
            name: Unique step name (must be non-empty)
            items_var: Variable name containing list (must be non-empty)
            loop_var: Variable name for current item (must be non-empty)
            loop_steps: Loop body steps (must be non-empty)
            output_var: Variable name for results (must be non-empty)
            max_iterations: Override max iterations limit (optional)
            is_critical: Whether failure aborts workflow (defaults to True)

        Raises:
            ValueError: If any required string is empty, loop_steps is empty,
                        or max_iterations <= 0
        """
        ...

    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute loop body for each item in collection.

        Execution flow:
            1. Resolve items_var from {**context.input_data, **context.previous_outputs}
            2. Validate items is a list
            3. Check iteration count against max_iterations limit
            4. For each item:
               a. Inject loop_var into child context.variables
               b. Execute loop_steps sequentially
               c. Collect output from iteration
               d. Aggregate token usage
            5. Return StepResult with collected results under output_var key

        Error Handling:
            - items_var not found → StepResult(status=FAILED, error="Variable 'X' not found")
            - items not a list → StepResult(status=FAILED, error="Expected list, got <type>")
            - len(items) > max_iterations → StepResult(status=FAILED, error="Max iterations exceeded")
            - Loop body step fails and is_critical → StepResult(status=FAILED, error="Iteration N: step 'X' failed")
            - Loop body step fails and not is_critical → log warning, continue

        Args:
            context: Execution context with input_data, previous_outputs, config

        Returns:
            StepResult with:
                - output: {output_var: [iteration_results]}
                - duration_ms: Total execution time (all iterations + overhead)
                - token_usage: Aggregated from all iterations' LLMStep calls
                - status: COMPLETED or FAILED

        Performance:
            - Per-iteration overhead: <0.1ms
            - 100-iteration degradation: ≤10% vs. 100 sequential plain steps (SC-003)
        """
        ...


class SwitchStep(WorkflowStep):
    """Multi-way dispatch workflow step (switch/case).

    Evaluates an expression and executes the steps for the matching case.
    If no case matches and default_steps are provided, executes default branch.

    Case Matching:
        - Expression result is converted to string: str(result)
        - Case keys are compared as strings (case-sensitive)
        - First matching case wins (dict order in Python 3.7+)

    Observability:
        Logs case match: "SwitchStep 'X' matched case 'Y' (value: 'Z')"
        Logs no match: "SwitchStep 'X' no match for value 'Z', executing default"

    Token Usage:
        Aggregates token usage from executed case/default branch.

    Examples:
        >>> from generative_ai_workflow import SwitchStep, LLMStep
        >>>
        >>> # Route by document type
        >>> SwitchStep(
        ...     name="type_router",
        ...     switch_on="document_type",     # Evaluate context variable
        ...     cases={
        ...         "email": [
        ...             LLMStep(name="process_email", prompt="Process email: {text}"),
        ...         ],
        ...         "report": [
        ...             LLMStep(name="process_report", prompt="Summarize report: {text}"),
        ...         ],
        ...         "invoice": [
        ...             LLMStep(name="process_invoice", prompt="Extract invoice data: {text}"),
        ...         ],
        ...     },
        ...     default_steps=[
        ...         LLMStep(name="process_unknown", prompt="Handle unknown type: {text}"),
        ...     ],
        ... )
        >>>
        >>> # Switch without default (fails if no match)
        >>> SwitchStep(
        ...     name="priority_router",
        ...     switch_on="priority",
        ...     cases={
        ...         "high": [LLMStep(name="escalate", prompt="Escalate: {issue}")],
        ...         "medium": [LLMStep(name="queue", prompt="Queue: {issue}")],
        ...         "low": [LLMStep(name="defer", prompt="Defer: {issue}")],
        ...     },
        ...     # No default_steps → fails if priority is "critical" or other unexpected value
        ... )
    """

    switch_on: str
    """Expression to evaluate (typically variable reference).

    Result is converted to string for case matching: str(result).
    Validated at workflow definition time for syntax, evaluated at runtime.

    Examples:
        "document_type"  → reads context.previous_outputs["document_type"]
        "priority"       → reads context.previous_outputs["priority"]
        "len(items)"     → evaluates expression, converts to string
    """

    cases: dict[str, list[WorkflowStep]]
    """Mapping of case values to step lists.

    Keys are case values (strings, case-sensitive).
    Values are lists of steps (must be non-empty per case).
    At least one case required.

    Example:
        {
            "email": [LLMStep(name="email_handler", ...)],
            "report": [LLMStep(name="report_handler", ...)],
        }
    """

    default_steps: list[WorkflowStep]
    """Steps executed if no case matches (optional).

    If omitted and no case matches, step fails with error.
    If provided, executed like any other case branch.
    """

    is_critical: bool
    """If True, step failure aborts workflow. If False, failure is logged and skipped."""

    def __init__(
        self,
        name: str,
        switch_on: str,
        cases: dict[str, list[WorkflowStep]],
        default_steps: list[WorkflowStep] | None = None,
        is_critical: bool = True,
    ) -> None:
        """Initialize switch step.

        Args:
            name: Unique step name (must be non-empty)
            switch_on: Expression to evaluate (must be non-empty)
            cases: Case value → step list mapping (must be non-empty)
            default_steps: Default branch steps (optional, defaults to [])
            is_critical: Whether failure aborts workflow (defaults to True)

        Raises:
            ValueError: If name is empty, switch_on is empty, cases is empty,
                        any case has empty steps, or switch_on has invalid syntax
        """
        ...

    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute steps for matching case.

        Execution flow:
            1. Evaluate switch_on expression on {**context.input_data, **context.previous_outputs}
            2. Convert result to string: str(result)
            3. Lookup case in cases dict (string match)
            4. If match found → execute case steps
            5. If no match and default_steps exist → execute default_steps
            6. If no match and no default_steps → return FAILED
            7. Accumulate outputs from executed steps

        Error Handling:
            - switch_on evaluation fails → StepResult(status=FAILED, error="Switch evaluation failed: ...")
            - No case matches and no default → StepResult(status=FAILED, error="No case matched value 'X'")
            - Case step fails and is_critical → StepResult(status=FAILED, error="Case 'X': step 'Y' failed: ...")
            - Case step fails and not is_critical → log warning, continue

        Args:
            context: Execution context with input_data, previous_outputs, config

        Returns:
            StepResult with:
                - output: Accumulated output from executed case/default steps
                - duration_ms: Total execution time (evaluation + case execution)
                - token_usage: Aggregated from nested LLMStep calls (if any)
                - status: COMPLETED or FAILED

        Performance:
            - Expression evaluation + case lookup: <0.2ms
            - Dispatch overhead: ≤5% vs. equivalent plain steps (SC-007)
        """
        ...


# =============================================================================
# Extended Configuration
# =============================================================================

# NOTE: WorkflowConfig is extended with new fields in the implementation.
# The contract is documented here for reference, but the actual extension
# happens in workflow.py to maintain backward compatibility.

# Extended WorkflowConfig fields (added to existing class):
#
#     max_iterations: int = Field(
#         default=100,
#         ge=1,
#         le=10000,
#         description="Maximum iterations for ForEachStep (DoW prevention)",
#     )
#
#     max_nesting_depth: int = Field(
#         default=5,
#         ge=1,
#         le=20,
#         description="Maximum control flow nesting depth (DoW prevention)",
#     )
#
# Usage:
#     from generative_ai_workflow import WorkflowConfig, Workflow
#
#     config = WorkflowConfig(
#         provider="openai",
#         max_iterations=50,  # Override default 100
#         max_nesting_depth=3,  # Override default 5
#     )
#     workflow = Workflow(steps=[...], config=config)


# =============================================================================
# Exception Types
# =============================================================================

class ExpressionError(Exception):
    """Raised when expression evaluation fails.

    Reasons:
        - Invalid syntax (AST parsing failure)
        - Undefined variable reference
        - Type mismatch (e.g., comparing str with int)
        - Forbidden operator (e.g., function definition, import)

    Examples:
        ExpressionError("Variable 'missing_var' not found in context (available: ['input', 'step1'])")
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
# Version Information
# =============================================================================

__version__ = "0.2.0"
__feature__ = "002-workflow-control-flow"
__date__ = "2026-02-08"

# Semantic versioning:
#   - MAJOR (X.0.0): Breaking changes to public API
#   - MINOR (0.X.0): New features, backward compatible (THIS RELEASE)
#   - PATCH (0.0.X): Bug fixes, no API changes

# Backward compatibility guarantee:
#   - All existing workflows (v0.1.0) work identically with v0.2.0
#   - New step types are additive (no modifications to existing classes)
#   - WorkflowConfig extended with optional fields (defaults preserve v0.1.0 behavior)
