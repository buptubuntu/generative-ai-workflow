"""Token usage tracking for workflow executions.

Accumulates per-step and total token usage, providing a query API
for cost tracking and observability (FR-011, FR-016).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from generative_ai_workflow.providers.base import TokenUsage


class TokenUsageTracker:
    """Accumulate and query token usage across workflow steps.

    Used internally by WorkflowEngine to track token consumption.
    Exposed via WorkflowResult.metrics for cost tracking applications.

    Example::

        tracker = TokenUsageTracker()
        tracker.record("summarize", response.usage)
        tracker.record("analyze", response.usage)
        total = tracker.total
        print(f"Total tokens: {total.total_tokens}")
    """

    def __init__(self) -> None:
        self._step_usage: dict[str, "TokenUsage"] = {}
        self._total: "TokenUsage | None" = None

    def record(self, step_name: str, usage: "TokenUsage") -> None:
        """Record token usage for a step.

        Args:
            step_name: The name of the workflow step.
            usage: Token usage from this step's LLM call.
        """
        self._step_usage[step_name] = usage
        self._accumulate(usage)

    def _accumulate(self, usage: "TokenUsage") -> None:
        """Add usage to the running total."""
        from generative_ai_workflow.providers.base import TokenUsage

        if self._total is None:
            self._total = usage
        else:
            prev = self._total
            self._total = TokenUsage(
                prompt_tokens=prev.prompt_tokens + usage.prompt_tokens,
                completion_tokens=prev.completion_tokens + usage.completion_tokens,
                total_tokens=prev.total_tokens + usage.total_tokens,
                model=usage.model,
                provider=usage.provider,
            )

    @property
    def total(self) -> "TokenUsage | None":
        """Aggregated token usage across all recorded steps."""
        return self._total

    def get_step_usage(self, step_name: str) -> "TokenUsage | None":
        """Get token usage for a specific step.

        Args:
            step_name: The step name to query.

        Returns:
            TokenUsage for the step, or None if not recorded.
        """
        return self._step_usage.get(step_name)

    @property
    def all_step_usage(self) -> dict[str, "TokenUsage"]:
        """All step usages as a dict of step_name -> TokenUsage."""
        return dict(self._step_usage)

    def reset(self) -> None:
        """Reset all accumulated usage."""
        self._step_usage.clear()
        self._total = None
