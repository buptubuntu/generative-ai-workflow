"""Middleware ABC for cross-cutting concerns (hooks).

Implement this interface to intercept LLM calls and workflow lifecycle
events without modifying framework core code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from generative_ai_workflow.providers.base import LLMRequest, LLMResponse
    from generative_ai_workflow.workflow import WorkflowResult


class Middleware:
    """Extension point for cross-cutting concerns (hooks).

    Implement this interface to intercept and modify LLM calls and
    workflow lifecycle events. Hook execution order is deterministic FIFO
    (registration order).

    Hooks can modify data by returning a modified object.
    Hooks can short-circuit by raising AbortError.

    Example::

        class CostTracker(Middleware):
            async def after_llm_call(
                self, response: LLMResponse, context: dict
            ) -> LLMResponse | None:
                log.info("llm_cost", tokens=response.usage.total_tokens)
                return None  # Don't modify response

        engine = WorkflowEngine()
        engine.use(CostTracker())
    """

    async def before_llm_call(
        self,
        request: "LLMRequest",
        context: dict[str, Any],
    ) -> "LLMRequest | None":
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
        self,
        response: "LLMResponse",
        context: dict[str, Any],
    ) -> "LLMResponse | None":
        """Hook executed after each LLM call.

        Args:
            response: The LLM response received.
            context: Execution context (workflow_id, step_id, etc.)

        Returns:
            Modified LLMResponse to use instead, or None to use original.
        """
        return None

    async def on_workflow_start(
        self,
        workflow_id: str,
        context: dict[str, Any],
    ) -> None:
        """Hook executed when a workflow begins execution."""

    async def on_workflow_end(
        self,
        result: "WorkflowResult",
        context: dict[str, Any],
    ) -> None:
        """Hook executed when a workflow completes (any terminal status)."""

    async def on_node_error(
        self,
        error: Exception,
        node_name: str,
        context: dict[str, Any],
    ) -> None:
        """Hook executed when a workflow node fails."""
