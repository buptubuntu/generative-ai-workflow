"""
Public Interface Contracts: generative_ai_workflow

This file defines all public-facing abstract interfaces (ABCs) that users
implement to extend the framework. These are the authoritative contracts
for the plugin system.

Note: This is a design artifact, not executable code. It serves as the
implementation blueprint for src/generative_ai_workflow/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

# ---------------------------------------------------------------------------
# Data Models (pydantic BaseModel — type signatures only)
# ---------------------------------------------------------------------------


class TokenUsage:
    """Token consumption record for a single LLM operation."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int  # validated: == prompt_tokens + completion_tokens
    model: str
    provider: str


class LLMRequest:
    """Input specification for an LLM completion call."""

    prompt: str
    model: str  # default: "gpt-4o-mini"
    temperature: float  # default: 0.7, range: [0.0, 2.0]
    max_tokens: int  # default: 1024
    system_prompt: str | None  # optional
    extra_params: dict[str, Any]  # provider-specific passthrough


class LLMResponse:
    """Output from an LLM completion call."""

    content: str
    model: str
    usage: TokenUsage
    latency_ms: float
    finish_reason: str  # "stop" | "length" | "error" | provider-specific


class StepContext:
    """Execution context passed to each workflow step."""

    workflow_id: str
    step_id: str
    correlation_id: str
    input_data: dict[str, Any]
    variables: dict[str, Any]  # for template substitution
    previous_outputs: dict[str, Any]  # step_name -> output
    config: "FrameworkConfig"


class StepResult:
    """Output from a single workflow step execution."""

    step_id: str
    status: str  # StepStatus enum value
    output: dict[str, Any] | None
    error: str | None
    duration_ms: float
    token_usage: TokenUsage | None


class WorkflowResult:
    """Final result of a complete workflow execution."""

    workflow_id: str
    correlation_id: str
    status: str  # WorkflowStatus enum value
    output: dict[str, Any] | None
    error: str | None
    metrics: "ExecutionMetrics"
    created_at: "datetime"
    completed_at: "datetime | None"


# ---------------------------------------------------------------------------
# Extension Point 1: LLM Provider
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """Extension point for LLM provider integrations.

    Implement this interface to add custom LLM providers (local models,
    alternative cloud providers, etc.) without modifying framework code.

    The framework ships with a built-in OpenAIProvider that implements
    this interface as a first-party plugin (dog-fooding).

    Registration:
        >>> from generative_ai_workflow import PluginRegistry
        >>> PluginRegistry.register_provider("my_provider", MyProvider)
        >>> workflow = Workflow(steps=[...], config=WorkflowConfig(provider="my_provider"))

    Example:
        >>> class MyProvider(LLMProvider):
        ...     async def complete_async(self, request: LLMRequest) -> LLMResponse:
        ...         response = await my_api.call(request.prompt)
        ...         return LLMResponse(
        ...             content=response.text,
        ...             model=request.model,
        ...             usage=TokenUsage(...),
        ...             latency_ms=response.elapsed_ms,
        ...             finish_reason="stop",
        ...         )
    """

    @abstractmethod
    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion asynchronously.

        Args:
            request: The LLM request specification.

        Returns:
            LLMResponse with content, token usage, and metadata.

        Raises:
            ProviderError: If the provider call fails after retries.
            ProviderAuthError: If authentication fails (non-retryable).
        """
        ...

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion synchronously.

        Default implementation runs complete_async in an event loop.
        Override for providers with native sync implementations.

        Args:
            request: The LLM request specification.

        Returns:
            LLMResponse with content, token usage, and metadata.
        """
        # Default: run async impl in event loop
        import asyncio
        return asyncio.run(self.complete_async(request))

    async def initialize(self) -> None:
        """Initialize provider resources (connections, credentials).

        Called once before first use. Override for providers requiring
        setup (connection pooling, credential validation, etc.).
        """

    async def cleanup(self) -> None:
        """Release provider resources.

        Called on framework shutdown. Override for providers requiring
        cleanup (closing connections, releasing locks, etc.).
        """


# ---------------------------------------------------------------------------
# Extension Point 2: Workflow Step
# ---------------------------------------------------------------------------


class WorkflowStep(ABC):
    """Extension point for custom workflow step types.

    Implement this interface to add new step behaviors (custom
    transformations, external API calls, data validation, etc.)
    without modifying the framework.

    The framework ships with built-in step types (LLMStep, TransformStep)
    that implement this interface.

    Attributes:
        name: Human-readable step identifier. Used in metrics and logs.
        is_critical: If True (default), step failure aborts the workflow.
            If False, failure is logged and execution continues.

    Example:
        >>> class SentimentStep(WorkflowStep):
        ...     name = "sentiment_analysis"
        ...
        ...     async def execute_async(self, context: StepContext) -> StepResult:
        ...         text = context.input_data.get("text", "")
        ...         sentiment = analyze(text)
        ...         return StepResult(
        ...             step_id=context.step_id,
        ...             status="completed",
        ...             output={"sentiment": sentiment},
        ...             error=None,
        ...             duration_ms=...,
        ...             token_usage=None,
        ...         )
    """

    name: str
    is_critical: bool = True

    @abstractmethod
    async def execute_async(self, context: StepContext) -> StepResult:
        """Execute this step asynchronously.

        Args:
            context: Execution context including input data, variables,
                     and outputs from previous steps.

        Returns:
            StepResult with output data and execution metadata.

        Raises:
            StepError: On unrecoverable step failure.
        """
        ...

    def execute(self, context: StepContext) -> StepResult:
        """Execute this step synchronously.

        Default implementation runs execute_async in an event loop.
        Override for steps with native sync implementations.
        """
        import asyncio
        return asyncio.run(self.execute_async(context))


# ---------------------------------------------------------------------------
# Extension Point 3: Middleware
# ---------------------------------------------------------------------------


class Middleware(ABC):
    """Extension point for cross-cutting concerns (hooks).

    Implement this interface to intercept and modify LLM calls and
    workflow lifecycle events without modifying framework core.

    Built-in framework behavior (logging, token tracking) is implemented
    as internal middleware using this same interface.

    Hook execution order: registration order (deterministic, FIFO).
    Hooks can modify data by returning a modified object.
    Hooks can short-circuit by raising AbortError.

    Example:
        >>> class CostTracker(Middleware):
        ...     async def after_llm_call(
        ...         self, response: LLMResponse, context: dict
        ...     ) -> LLMResponse | None:
        ...         log.info("llm_cost", tokens=response.usage.total_tokens)
        ...         return None  # Don't modify response
        ...
        >>> engine = WorkflowEngine()
        >>> engine.use(CostTracker())
    """

    async def before_llm_call(
        self, request: LLMRequest, context: dict[str, Any]
    ) -> LLMRequest | None:
        """Hook executed before each LLM call.

        Args:
            request: The LLM request about to be sent.
            context: Execution context (workflow_id, step_id, etc.)

        Returns:
            Modified LLMRequest to use instead, or None to use original.

        Raises:
            AbortError: To prevent the LLM call from proceeding.
        """
        return None

    async def after_llm_call(
        self, response: LLMResponse, context: dict[str, Any]
    ) -> LLMResponse | None:
        """Hook executed after each LLM call.

        Args:
            response: The LLM response received.
            context: Execution context (workflow_id, step_id, etc.)

        Returns:
            Modified LLMResponse to use instead, or None to use original.
        """
        return None

    async def on_workflow_start(
        self, workflow_id: str, context: dict[str, Any]
    ) -> None:
        """Hook executed when a workflow begins execution."""

    async def on_workflow_end(
        self, result: WorkflowResult, context: dict[str, Any]
    ) -> None:
        """Hook executed when a workflow completes (any terminal status)."""

    async def on_step_error(
        self,
        error: Exception,
        step_name: str,
        context: dict[str, Any],
    ) -> None:
        """Hook executed when a workflow step fails."""


# ---------------------------------------------------------------------------
# Core Public API (not abstract — user-facing classes)
# ---------------------------------------------------------------------------


class Workflow:
    """Define and execute a multi-step LLM workflow.

    A workflow is an ordered sequence of steps executed with data flowing
    from one step to the next.

    Args:
        steps: Ordered list of workflow steps to execute.
        name: Optional human-readable name for logging and metrics.
        config: Optional workflow-specific configuration overrides.

    Usage (async — recommended):
        >>> workflow = Workflow(steps=[prompt_step, llm_step, parse_step])
        >>> result = await workflow.execute_async({"user_input": "Hello"})
        >>> print(result.output)

    Usage (sync with timeout):
        >>> result = workflow.execute({"user_input": "Hello"}, timeout=30.0)
        >>> print(result.status)  # "completed" or "timeout"
    """

    def __init__(
        self,
        steps: list[WorkflowStep],
        name: str = "",
        config: "WorkflowConfig | None" = None,
    ) -> None: ...

    async def execute_async(
        self,
        input_data: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> WorkflowResult:
        """Execute the workflow asynchronously (non-blocking).

        Args:
            input_data: Input data dictionary passed to the first step.
            correlation_id: Optional tracing ID. Auto-generated if not provided.

        Returns:
            WorkflowResult with status, output, and execution metrics.
        """
        ...

    def execute(
        self,
        input_data: dict[str, Any],
        *,
        timeout: float | None = None,
        correlation_id: str | None = None,
    ) -> WorkflowResult:
        """Execute the workflow synchronously (blocking).

        Args:
            input_data: Input data dictionary passed to the first step.
            timeout: Optional timeout in seconds. If exceeded, returns
                     WorkflowResult with status=TIMEOUT and execution state.
            correlation_id: Optional tracing ID. Auto-generated if not provided.

        Returns:
            WorkflowResult with status, output, and execution metrics.
        """
        ...


class PluginRegistry:
    """Register and discover framework plugins.

    Central registry for LLM providers and custom step types.
    The built-in OpenAI provider is pre-registered as "openai".

    Example:
        >>> PluginRegistry.register_provider("my_llm", MyLLMProvider)
        >>> provider = PluginRegistry.get_provider("my_llm")
    """

    @classmethod
    def register_provider(cls, name: str, provider_class: type[LLMProvider]) -> None:
        """Register a custom LLM provider.

        Args:
            name: Unique provider identifier used in workflow configuration.
            provider_class: LLMProvider subclass to register.

        Raises:
            PluginRegistrationError: If name is already registered or class
                                      does not implement LLMProvider.
        """
        ...

    @classmethod
    def get_provider(cls, name: str) -> LLMProvider:
        """Get an initialized LLM provider instance.

        Args:
            name: Provider identifier (as registered).

        Returns:
            Initialized LLMProvider instance.

        Raises:
            PluginNotFoundError: If provider name not registered.
        """
        ...

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        ...


class WorkflowEngine:
    """Configure and execute workflows with middleware support.

    Central execution engine with middleware pipeline, retry logic,
    and observability integration.

    Example:
        >>> engine = WorkflowEngine()
        >>> engine.use(CostTrackingMiddleware())
        >>> engine.use(LoggingMiddleware())
        >>> result = await engine.run_async(workflow, input_data)
    """

    def __init__(self, config: "FrameworkConfig | None" = None) -> None: ...

    def use(self, middleware: Middleware) -> "WorkflowEngine":
        """Register middleware (executed in registration order).

        Args:
            middleware: Middleware instance to add to the pipeline.

        Returns:
            Self for chaining: engine.use(A).use(B).use(C)
        """
        ...

    async def run_async(
        self,
        workflow: Workflow,
        input_data: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> WorkflowResult:
        """Execute a workflow through the full middleware pipeline."""
        ...

    def run(
        self,
        workflow: Workflow,
        input_data: dict[str, Any],
        *,
        timeout: float | None = None,
        correlation_id: str | None = None,
    ) -> WorkflowResult:
        """Execute a workflow synchronously through the full middleware pipeline."""
        ...
