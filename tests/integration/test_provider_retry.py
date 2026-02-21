"""Integration tests for LLM provider retry behavior (FR-012)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from generative_ai_workflow import (
    LLMNode,
    PluginRegistry,
    Workflow,
    WorkflowConfig,
    WorkflowStatus,
)
from generative_ai_workflow.providers.openai import OpenAIProvider


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    PluginRegistry.clear()
    yield


@pytest.mark.integration
class TestProviderRetryBehavior:
    """Verify retry with exponential backoff (mocked, no real API)."""

    async def test_rate_limit_retries_succeed(self) -> None:
        """Provider retries on 429 and eventually succeeds."""
        import openai

        from generative_ai_workflow.providers.base import LLMRequest

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Retry success"
        mock_completion.choices[0].finish_reason = "stop"
        mock_completion.model = "gpt-4o-mini"
        mock_completion.usage = MagicMock(prompt_tokens=5, completion_tokens=3, total_tokens=8)

        call_count = 0
        mock_client = AsyncMock()

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise openai.RateLimitError(
                    "rate limited",
                    response=MagicMock(status_code=429),
                    body=None,
                )
            return mock_completion

        mock_client.chat.completions.create = side_effect

        provider = OpenAIProvider(api_key="sk-test", max_retries=3, backoff_factor=0.01)
        provider._client = mock_client
        PluginRegistry.register_provider("openai-retry", provider)

        workflow = Workflow(
            nodes=[LLMNode(name="gen", prompt="Hello {text}", provider="openai-retry")],
            config=WorkflowConfig(provider="openai-retry"),
        )
        result = await workflow.execute_async({"text": "world"})
        assert result.status == WorkflowStatus.COMPLETED
        assert call_count == 2

    async def test_max_retries_exhausted_fails_workflow(self) -> None:
        """After max retries, workflow transitions to FAILED."""
        import openai

        mock_client = AsyncMock()

        async def always_rate_limit(*args, **kwargs):
            raise openai.RateLimitError(
                "rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )

        mock_client.chat.completions.create = always_rate_limit

        provider = OpenAIProvider(api_key="sk-test", max_retries=2, backoff_factor=0.01)
        provider._client = mock_client
        PluginRegistry.register_provider("openai-fail", provider)

        workflow = Workflow(
            nodes=[LLMNode(name="gen", prompt="Hello {text}", provider="openai-fail")],
            config=WorkflowConfig(provider="openai-fail"),
        )
        result = await workflow.execute_async({"text": "world"})
        assert result.status == WorkflowStatus.FAILED
