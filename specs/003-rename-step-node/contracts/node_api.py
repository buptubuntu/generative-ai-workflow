"""Public API contracts for the generative_ai_workflow node types.

This file documents the complete public interface after the Step → Node rename
(feature 003-rename-step-node). It serves as the authoritative contract for
both implementers of WorkflowNode and consumers of LLMNode / TransformNode /
ConditionalNode.

All names previously containing "Step" are replaced. Old names are removed
with no backward-compatible aliases.

Feature: 003-rename-step-node
Date: 2026-02-21
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Execution Model Types  (formerly StepContext, StepResult, StepStatus)
# ---------------------------------------------------------------------------


class NodeStatus:
    """Lifecycle states of a single workflow node execution.

    Values:
        PENDING:   Node is queued but not yet started.
        RUNNING:   Node is actively executing.
        COMPLETED: Node finished successfully.
        FAILED:    Node encountered an unrecoverable error.
        SKIPPED:   Node was bypassed (e.g., non-critical failure upstream).

    Property:
        is_terminal: True for COMPLETED, FAILED, SKIPPED.
    """

    PENDING: str
    RUNNING: str
    COMPLETED: str
    FAILED: str
    SKIPPED: str

    @property
    def is_terminal(self) -> bool: ...


class NodeContext:
    """Execution context passed to each workflow node.

    Attributes:
        workflow_id:      Parent workflow UUID.
        step_id:          Execution-slot UUID (renamed to node_id in a future pass).
        correlation_id:   Distributed tracing correlation UUID.
        input_data:       Original input data passed to Workflow.execute_async().
        variables:        Template substitution variables.
        previous_outputs: Accumulated outputs from all prior nodes, keyed by node name.
        config:           Merged FrameworkConfig for this execution.
    """

    workflow_id: str
    step_id: str          # Note: retains 'step_id' name in this release
    correlation_id: str
    input_data: dict[str, Any]
    variables: dict[str, Any]
    previous_outputs: dict[str, Any]
    config: Any           # FrameworkConfig | None


class NodeResult:
    """Result returned from a single workflow node execution.

    Attributes:
        step_id:      Execution-slot UUID.
        status:       Terminal NodeStatus (COMPLETED, FAILED, or SKIPPED).
        output:       Node output dict — None if node failed.
        error:        Error message string — None if node succeeded.
        duration_ms:  Wall-clock execution time in milliseconds (≥ 0).
        token_usage:  TokenUsage if this node made an LLM call, else None.
    """

    step_id: str
    status: NodeStatus
    output: dict[str, Any] | None
    error: str | None
    duration_ms: float
    token_usage: Any | None   # TokenUsage | None


# ---------------------------------------------------------------------------
# Exception  (formerly StepError)
# ---------------------------------------------------------------------------


class NodeError(Exception):
    """Raised on unrecoverable workflow node failure.

    Inherits from FrameworkError. Raised by node implementations when
    an error is unrecoverable and should abort the workflow.

    Example::

        raise NodeError(f"External service unavailable: {url}")
    """
    ...


# ---------------------------------------------------------------------------
# Abstract Base  (formerly WorkflowStep)
# ---------------------------------------------------------------------------


class WorkflowNode(ABC):
    """Abstract base class for all workflow node implementations.

    Implement this interface to add custom node behaviors to a workflow
    without modifying framework code.

    Attributes:
        name:        Human-readable node identifier. Used in metrics, logs,
                     and as the key in previous_outputs for downstream nodes.
                     Must be non-empty and unique within a Workflow.
        is_critical: If True (default), node failure aborts the workflow.
                     If False, failure is logged and execution continues.

    Example::

        class SentimentNode(WorkflowNode):
            name = "sentiment_analysis"

            async def execute_async(self, context: NodeContext) -> NodeResult:
                text = context.input_data.get("text", "")
                sentiment = analyze(text)
                return NodeResult(
                    step_id=context.step_id,
                    status=NodeStatus.COMPLETED,
                    output={"sentiment": sentiment},
                    error=None,
                    duration_ms=0.0,
                )
    """

    name: str = ""
    is_critical: bool = True

    def __init__(self, name: str = "", is_critical: bool = True) -> None:
        """Initialise the node.

        Args:
            name:        Node identifier. Must be non-empty.
            is_critical: Whether failure aborts the workflow.

        Raises:
            ValueError: If name is empty.
        """
        ...

    @abstractmethod
    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Execute this node asynchronously.

        Args:
            context: Execution context with input data and accumulated
                     outputs from all prior nodes.

        Returns:
            NodeResult with output data and execution metadata.

        Raises:
            NodeError: On unrecoverable node failure.
        """
        ...

    def execute(self, context: NodeContext) -> NodeResult:
        """Execute this node synchronously.

        Default implementation wraps execute_async in an event loop.
        Override for nodes with native synchronous implementations.

        Args:
            context: Execution context.

        Returns:
            NodeResult with output data.
        """
        ...


# ---------------------------------------------------------------------------
# Built-in Nodes  (formerly LLMStep, TransformStep)
# ---------------------------------------------------------------------------


class LLMNode(WorkflowNode):
    """A node that calls an LLM provider with a prompt template.

    The prompt supports {variable} placeholders substituted from the
    accumulated context data (input_data merged with previous_outputs).

    Args:
        name:        Node identifier.
        prompt:      Prompt template with optional {variable} placeholders.
        provider:    Provider name override (default: workflow config default).
        is_critical: Whether node failure aborts the workflow.

    Attributes:
        prompt_template: The prompt string as supplied.
        provider_name:   Resolved provider name (or None to use default).

    Example::

        node = LLMNode(
            name="summarize",
            prompt="Summarize in one sentence: {text}",
        )

    Performance:
        Token usage is captured in NodeResult.token_usage for every call.
        Latency is captured in NodeResult.duration_ms.
    """

    def __init__(
        self,
        name: str,
        prompt: str,
        provider: str | None = None,
        is_critical: bool = True,
    ) -> None:
        """Initialise LLMNode.

        Args:
            name:        Node identifier.
            prompt:      Non-empty prompt template.
            provider:    Provider name override.
            is_critical: Whether failure aborts the workflow.

        Raises:
            ValueError: If name or prompt is empty.
        """
        ...

    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Render prompt, call LLM provider, return result.

        Args:
            context: Execution context with input data and prior outputs.

        Returns:
            NodeResult with LLM response text and TokenUsage.

        Raises:
            NodeError: If prompt rendering or LLM call fails unrecoverably.
        """
        ...


class TransformNode(WorkflowNode):
    """A node that applies a pure Python transformation to context data.

    No LLM call is made. The transform callable receives the merged dict
    of {**input_data, **previous_outputs} and must return a dict.

    Args:
        name:        Node identifier.
        transform:   Callable[[dict[str, Any]], dict[str, Any]].
        is_critical: Whether node failure aborts the workflow.

    Example::

        node = TransformNode(
            name="prepare",
            transform=lambda data: {"prompt_input": data["text"].strip()},
        )
    """

    def __init__(
        self,
        name: str,
        transform: Callable[[dict[str, Any]], dict[str, Any]],
        is_critical: bool = True,
    ) -> None: ...

    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Apply the transform callable to accumulated context data.

        Args:
            context: Execution context.

        Returns:
            NodeResult with the dict returned by transform.

        Raises:
            NodeError: If the transform callable raises an exception.
        """
        ...


# ---------------------------------------------------------------------------
# Control Flow Node  (formerly ConditionalStep)
# ---------------------------------------------------------------------------


class ConditionalNode:
    """Conditional branching workflow node (if/else).

    Evaluates a boolean expression against the accumulated context data
    and executes either the true_nodes or false_nodes branch.

    Note: Does not inherit WorkflowNode — duck-typed with execute_async,
    matching the pattern of the former ConditionalStep.

    Args:
        name:        Node identifier.
        condition:   Boolean expression string evaluated via ExpressionEvaluator.
                     Supported operators: ==, !=, <, >, <=, >=, in, not in,
                     and, or, not.
                     Example: "sentiment == 'positive'"
        true_nodes:  Nodes to execute if condition evaluates to True.
                     Must be non-empty.
        false_nodes: Nodes to execute if condition evaluates to False.
                     Optional; defaults to [] (no-op else branch).
        is_critical: Whether node failure aborts the workflow.

    Example::

        node = ConditionalNode(
            name="sentiment_router",
            condition="sentiment == 'positive'",
            true_nodes=[LLMNode(name="positive_response", prompt="...")],
            false_nodes=[LLMNode(name="negative_response", prompt="...")],
        )

    Raises:
        ValueError: If name is empty, condition is empty, or true_nodes is empty.
        ExpressionError: If condition syntax is invalid (checked at construction).
    """

    name: str
    condition: str
    true_nodes: list[WorkflowNode]
    false_nodes: list[WorkflowNode]
    is_critical: bool

    def __init__(
        self,
        name: str,
        condition: str,
        true_nodes: list[WorkflowNode],
        false_nodes: list[WorkflowNode] | None = None,
        is_critical: bool = True,
    ) -> None: ...

    async def execute_async(self, context: NodeContext) -> NodeResult:
        """Evaluate condition and execute selected branch.

        Args:
            context: Execution context with input data and prior outputs.

        Returns:
            NodeResult with accumulated output from executed branch nodes.
            Token usage is aggregated across all branch nodes.

        Error handling:
            - Condition evaluation failure → NodeResult(status=FAILED)
            - Critical child node failure  → NodeResult(status=FAILED)
            - Non-critical child failure   → logged, execution continues
        """
        ...


# ---------------------------------------------------------------------------
# Workflow (updated constructor signature)
# ---------------------------------------------------------------------------


class Workflow:
    """Define and execute a multi-node LLM workflow.

    A workflow is an ordered sequence of nodes executed with data flowing
    from one node to the next. Each node receives the accumulated outputs
    from all prior nodes.

    Args:
        nodes:  Ordered list of workflow nodes to execute.
                (Formerly: steps= parameter — hard-renamed to nodes=)
        name:   Optional human-readable name for logging and metrics.
        config: Optional WorkflowConfig overrides.

    Attributes:
        nodes:       The ordered list of nodes (formerly .steps).
        name:        Workflow name.
        config:      Resolved WorkflowConfig.
        workflow_id: Auto-generated UUID.

    Usage (async — recommended)::

        workflow = Workflow(
            nodes=[
                TransformNode(name="prep", transform=lambda d: {"text": d["raw"].strip()}),
                LLMNode(name="summarize", prompt="Summarize: {text}"),
            ]
        )
        result = await workflow.execute_async({"raw": "Long article..."})
        print(result.status)
        print(result.metrics.token_usage_total.total_tokens)

    Usage (sync with timeout)::

        result = workflow.execute({"raw": "..."}, timeout=30.0)
        print(result.status)

    Raises:
        ValueError: If nodes is empty or contains duplicate node names.
    """

    def __init__(
        self,
        nodes: list[WorkflowNode],
        name: str = "",
        config: Any = None,  # WorkflowConfig | None
    ) -> None: ...

    async def execute_async(
        self,
        input_data: dict[str, Any],
        *,
        correlation_id: str | None = None,
        framework_config: Any = None,  # FrameworkConfig | None
    ) -> Any:  # WorkflowResult
        """Execute the workflow asynchronously.

        Args:
            input_data:       Input dict passed to the first node.
            correlation_id:   Optional tracing ID (auto-generated if None).
            framework_config: Optional FrameworkConfig override.

        Returns:
            WorkflowResult with status, output, and ExecutionMetrics.
        """
        ...

    def execute(
        self,
        input_data: dict[str, Any],
        *,
        timeout: float | None = None,
        correlation_id: str | None = None,
        framework_config: Any = None,
    ) -> Any:  # WorkflowResult
        """Execute the workflow synchronously.

        Args:
            input_data:       Input dict passed to the first node.
            timeout:          Optional timeout in seconds.
            correlation_id:   Optional tracing ID.
            framework_config: Optional FrameworkConfig override.

        Returns:
            WorkflowResult with status=TIMEOUT if timeout exceeded.
        """
        ...
