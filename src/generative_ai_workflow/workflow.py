"""Workflow data models and the Workflow class.

Contains all pydantic models for workflow state management plus the
Workflow class that users construct to define multi-node LLM pipelines.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from generative_ai_workflow.config import FrameworkConfig
    from generative_ai_workflow.node import WorkflowNode


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkflowStatus(str, Enum):
    """Lifecycle states of a workflow execution.

    State transitions::

        PENDING → RUNNING → COMPLETED
                          → FAILED
                          → CANCELLED
                          → TIMEOUT
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    @property
    def is_terminal(self) -> bool:
        """Return True if this is a terminal (final) state."""
        return self in (
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.TIMEOUT,
        )


class NodeStatus(str, Enum):
    """Lifecycle states of a single workflow node."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def is_terminal(self) -> bool:
        """Return True if this is a terminal (final) state."""
        return self in (
            NodeStatus.COMPLETED,
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
        )


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class NodeContext(BaseModel):
    """Execution context passed to each workflow node.

    Attributes:
        workflow_id: Parent workflow UUID.
        step_id: Execution-slot UUID.
        correlation_id: Distributed tracing correlation UUID.
        input_data: Data passed to this node.
        variables: Template substitution variables.
        previous_outputs: Outputs from prior nodes, keyed by node name.
        config: Merged configuration for this execution.
    """

    workflow_id: str
    step_id: str
    correlation_id: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    previous_outputs: dict[str, Any] = Field(default_factory=dict)
    config: Any = Field(default=None)  # FrameworkConfig — Any to avoid circular at model level


class NodeResult(BaseModel):
    """Output from a single workflow node execution.

    Attributes:
        step_id: Execution-slot UUID.
        status: Terminal execution status.
        output: Node output data (None if node failed).
        error: Error message if the node failed.
        duration_ms: Node execution wall-clock time.
        token_usage: Token consumption if this node involved an LLM call.
    """

    step_id: str
    status: NodeStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = Field(ge=0.0)
    token_usage: Any | None = None  # TokenUsage | None — imported lazily


class ExecutionMetrics(BaseModel):
    """Aggregated performance and observability data for a workflow execution.

    Attributes:
        total_duration_ms: Wall-clock time from start to completion.
        step_durations: step_name → duration_ms mapping.
        token_usage_total: Aggregated token usage across all LLM steps.
        step_token_usage: step_name → TokenUsage mapping.
        steps_completed: Count of COMPLETED steps.
        steps_failed: Count of FAILED steps.
        steps_skipped: Count of SKIPPED steps.
    """

    total_duration_ms: float = Field(default=0.0, ge=0.0)
    step_durations: dict[str, float] = Field(default_factory=dict)
    token_usage_total: Any | None = None  # TokenUsage | None
    step_token_usage: dict[str, Any] = Field(default_factory=dict)  # str → TokenUsage
    steps_completed: int = Field(default=0, ge=0)
    steps_failed: int = Field(default=0, ge=0)
    steps_skipped: int = Field(default=0, ge=0)


class WorkflowResult(BaseModel):
    """Final result returned to the caller after workflow execution.

    Attributes:
        workflow_id: Workflow UUID.
        correlation_id: Distributed tracing correlation UUID.
        status: Terminal workflow status.
        output: Final step output data.
        error: Error message if the workflow failed.
        metrics: Full observability data.
        created_at: UTC creation timestamp.
        completed_at: UTC completion timestamp (None if not yet complete).
    """

    workflow_id: str
    correlation_id: str
    status: WorkflowStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Input Validation Helpers (FR-029)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+previous", re.IGNORECASE),
    re.compile(r"\breveal\b", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
]


def _check_injection(text: str) -> None:
    """Raise ValueError if text contains basic injection patterns."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise ValueError(
                f"Input contains potentially unsafe content matching pattern "
                f"{pattern.pattern!r}. Review and sanitize input before use."
            )


def _validate_input_data(data: dict[str, Any]) -> None:
    """Recursively validate string values in input data for injection patterns."""
    for value in data.values():
        if isinstance(value, str):
            _check_injection(value)
        elif isinstance(value, dict):
            _validate_input_data(value)


# ---------------------------------------------------------------------------
# WorkflowConfig
# ---------------------------------------------------------------------------


class WorkflowConfig(BaseModel):
    """Per-workflow configuration overrides.

    Attributes:
        provider: LLM provider name to use (overrides framework default).
        model: LLM model override.
        temperature: Temperature override.
        max_tokens: Max tokens override.
        max_iterations: Maximum loop iterations (default: 100, prevents runaway loops).
        max_nesting_depth: Maximum control flow nesting depth (default: 5).
    """

    provider: str = Field(default="openai")
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    max_iterations: int = Field(default=100, ge=1, le=10000)
    max_nesting_depth: int = Field(default=5, ge=1, le=20)


# ---------------------------------------------------------------------------
# Workflow Class
# ---------------------------------------------------------------------------


class Workflow:
    """Define and execute a multi-node LLM workflow.

    A workflow is an ordered sequence of nodes executed with data flowing
    from one node to the next. Each node receives the accumulated outputs
    from all prior nodes.

    Args:
        nodes: Ordered list of workflow nodes to execute.
        name: Optional human-readable name for logging and metrics.
        config: Optional workflow-specific configuration overrides.

    Usage (async — recommended)::

        workflow = Workflow(nodes=[prep_node, llm_node, parse_node])
        result = await workflow.execute_async({"user_input": "Hello"})
        print(result.output)

    Usage (sync with timeout)::

        result = workflow.execute({"user_input": "Hello"}, timeout=30.0)
        print(result.status)  # "completed" or "timeout"
    """

    def __init__(
        self,
        nodes: list["WorkflowNode"],
        name: str = "",
        config: WorkflowConfig | None = None,
    ) -> None:
        if not nodes:
            raise ValueError("Workflow must have at least one node.")
        self._validate_nodes(nodes)
        self.nodes = nodes
        self.name = name
        self.config = config or WorkflowConfig()
        self.workflow_id = str(uuid.uuid4())

    @staticmethod
    def _validate_nodes(nodes: list["WorkflowNode"]) -> None:
        """Validate node names are non-empty and unique."""
        seen: set[str] = set()
        for node in nodes:
            if not node.name:
                raise ValueError("All workflow nodes must have a non-empty name.")
            if node.name in seen:
                raise ValueError(f"Duplicate node name: {node.name!r}")
            seen.add(node.name)

    async def execute_async(
        self,
        input_data: dict[str, Any],
        *,
        correlation_id: str | None = None,
        framework_config: "FrameworkConfig | None" = None,
    ) -> WorkflowResult:
        """Execute the workflow asynchronously (non-blocking).

        Args:
            input_data: Input data dictionary passed to the first step.
            correlation_id: Optional tracing ID. Auto-generated if not provided.
            framework_config: Optional framework configuration override.

        Returns:
            WorkflowResult with status, output, and execution metrics.
        """
        from generative_ai_workflow.engine import WorkflowEngine
        engine = WorkflowEngine(config=framework_config)
        return await engine.run_async(self, input_data, correlation_id=correlation_id)

    def execute(
        self,
        input_data: dict[str, Any],
        *,
        timeout: float | None = None,
        correlation_id: str | None = None,
        framework_config: "FrameworkConfig | None" = None,
    ) -> WorkflowResult:
        """Execute the workflow synchronously (blocking).

        Args:
            input_data: Input data dictionary passed to the first step.
            timeout: Optional timeout in seconds. If exceeded, returns
                     WorkflowResult with status=TIMEOUT and execution state.
            correlation_id: Optional tracing ID. Auto-generated if not provided.
            framework_config: Optional framework configuration override.

        Returns:
            WorkflowResult with status, output, and execution metrics.
        """
        from generative_ai_workflow.engine import WorkflowEngine
        engine = WorkflowEngine(config=framework_config)
        return engine.run(self, input_data, timeout=timeout, correlation_id=correlation_id)
