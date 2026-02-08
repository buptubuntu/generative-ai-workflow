"""Shared pytest fixtures for generative_ai_workflow test suite."""

from __future__ import annotations

from typing import Any

import pytest

from generative_ai_workflow.config import FrameworkConfig
from generative_ai_workflow.providers.mock import MockLLMProvider


@pytest.fixture
def framework_config() -> FrameworkConfig:
    """Provide a test-safe FrameworkConfig with no real API keys."""
    return FrameworkConfig(
        openai_api_key="sk-test-key",  # noqa: S106 - test fixture
        default_model="gpt-4o-mini",
        default_temperature=0.7,
        default_max_tokens=256,
        log_level="DEBUG",
    )


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    """Provide a MockLLMProvider with a default canned response."""
    return MockLLMProvider(
        responses={"default": "This is a mock LLM response."},
    )


@pytest.fixture
def cost_tracker() -> "CostTracker":
    """Fixture that tracks token usage and enforces per-test cost budget.

    Usage::

        def test_something(cost_tracker):
            result = workflow.execute(...)
            cost_tracker.record(result.metrics.token_usage_total)
            cost_tracker.assert_within_budget()
    """
    return CostTracker(max_tokens_per_test=50_000)  # ~$0.10 at gpt-4o-mini pricing


class CostTracker:
    """Tracks token usage and enforces cost budgets in tests."""

    # gpt-4o-mini pricing as of 2026 (approximate)
    COST_PER_1K_PROMPT = 0.00015
    COST_PER_1K_COMPLETION = 0.0006

    def __init__(self, max_tokens_per_test: int = 50_000) -> None:
        self.max_tokens_per_test = max_tokens_per_test
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

    def record(self, token_usage: Any | None) -> None:
        """Record token usage from a TokenUsage instance."""
        if token_usage is None:
            return
        self._total_prompt_tokens += token_usage.prompt_tokens
        self._total_completion_tokens += token_usage.completion_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed across all recorded operations."""
        return self._total_prompt_tokens + self._total_completion_tokens

    @property
    def estimated_cost_usd(self) -> float:
        """Estimated cost in USD based on gpt-4o-mini pricing."""
        return (
            self._total_prompt_tokens / 1000 * self.COST_PER_1K_PROMPT
            + self._total_completion_tokens / 1000 * self.COST_PER_1K_COMPLETION
        )

    def assert_within_budget(self) -> None:
        """Assert that token usage is within the configured budget."""
        assert self.total_tokens <= self.max_tokens_per_test, (
            f"Test exceeded token budget: {self.total_tokens} > {self.max_tokens_per_test}. "
            f"Estimated cost: ${self.estimated_cost_usd:.4f}"
        )
