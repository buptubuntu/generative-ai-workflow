"""Unit tests for OpenAIProvider using mock patches (no real API calls)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from generative_ai_workflow import ProviderAuthError, ProviderError
from generative_ai_workflow.providers.base import LLMRequest
from generative_ai_workflow.providers.openai import OpenAIProvider


def _make_mock_completion(
    content: str = "Hello!",
    model: str = "gpt-4o-mini",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    finish_reason: str = "stop",
) -> MagicMock:
    """Create a mock OpenAI ChatCompletion response."""
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = prompt_tokens + completion_tokens

    choice = MagicMock()
    choice.message.content = content
    choice.finish_reason = finish_reason

    completion = MagicMock()
    completion.choices = [choice]
    completion.model = model
    completion.usage = usage
    return completion


class TestOpenAIProviderSuccess:
    """Happy-path tests for OpenAIProvider."""

    async def test_complete_async_returns_response(self) -> None:
        mock_completion = _make_mock_completion("Test output")
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        provider = OpenAIProvider(api_key="sk-test")
        provider._client = mock_client

        response = await provider.complete_async(
            LLMRequest(prompt="Hello", model="gpt-4o-mini")
        )

        assert response.content == "Test output"
        assert response.model == "gpt-4o-mini"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.usage.total_tokens == 15

    async def test_token_usage_extracted_correctly(self) -> None:
        mock_completion = _make_mock_completion(
            content="Response text",
            prompt_tokens=20,
            completion_tokens=8,
        )
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        provider = OpenAIProvider(api_key="sk-test")
        provider._client = mock_client

        response = await provider.complete_async(LLMRequest(prompt="Test"))
        assert response.usage.prompt_tokens == 20
        assert response.usage.completion_tokens == 8
        assert response.usage.total_tokens == 28

    async def test_finish_reason_captured(self) -> None:
        mock_completion = _make_mock_completion(finish_reason="length")
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        provider = OpenAIProvider(api_key="sk-test")
        provider._client = mock_client

        response = await provider.complete_async(LLMRequest(prompt="Test"))
        assert response.finish_reason == "length"

    async def test_latency_ms_positive(self) -> None:
        mock_completion = _make_mock_completion()
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        provider = OpenAIProvider(api_key="sk-test")
        provider._client = mock_client

        response = await provider.complete_async(LLMRequest(prompt="Test"))
        assert response.latency_ms >= 0.0


class TestOpenAIProviderRetry:
    """Tests for retry behavior (FR-012)."""

    async def test_retries_on_rate_limit(self) -> None:
        """429-equivalent errors should trigger retry."""
        import openai

        mock_completion = _make_mock_completion("Success after retry")
        mock_client = AsyncMock()
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise openai.RateLimitError(
                    "rate limited",
                    response=MagicMock(status_code=429),
                    body=None,
                )
            return mock_completion

        mock_client.chat.completions.create = side_effect

        provider = OpenAIProvider(api_key="sk-test", max_retries=3, backoff_factor=0.01)
        provider._client = mock_client

        response = await provider.complete_async(LLMRequest(prompt="Test"))
        assert response.content == "Success after retry"
        assert call_count == 3

    async def test_auth_error_raises_immediately(self) -> None:
        """Auth errors should raise ProviderAuthError without retry."""
        import openai

        mock_client = AsyncMock()
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise openai.AuthenticationError(
                "invalid key",
                response=MagicMock(status_code=401),
                body=None,
            )

        mock_client.chat.completions.create = side_effect

        provider = OpenAIProvider(api_key="sk-bad", max_retries=3, backoff_factor=0.01)
        provider._client = mock_client

        with pytest.raises((ProviderAuthError, ProviderError)):
            await provider.complete_async(LLMRequest(prompt="Test"))
        # Auth errors should not retry
        assert call_count == 1


class TestOpenAIProviderMockProvider:
    """Tests for MockLLMProvider (FR-031)."""

    async def test_mock_returns_canned_response(self) -> None:
        from generative_ai_workflow import MockLLMProvider

        mock = MockLLMProvider(responses={"default": "Canned response."})
        response = await mock.complete_async(LLMRequest(prompt="anything"))
        assert response.content == "Canned response."
        assert response.usage.total_tokens > 0

    def test_mock_sync_works(self) -> None:
        from generative_ai_workflow import MockLLMProvider

        mock = MockLLMProvider(responses={"default": "Sync response."})
        response = mock.complete(LLMRequest(prompt="anything"))
        assert response.content == "Sync response."

    async def test_mock_call_count_tracked(self) -> None:
        from generative_ai_workflow import MockLLMProvider

        mock = MockLLMProvider(responses={"default": "r"})
        await mock.complete_async(LLMRequest(prompt="1"))
        await mock.complete_async(LLMRequest(prompt="2"))
        assert mock.call_count == 2

    async def test_mock_fail_with_raises(self) -> None:
        from generative_ai_workflow import MockLLMProvider, ProviderError

        mock = MockLLMProvider(fail_with=ProviderError("simulated failure"))
        with pytest.raises(ProviderError, match="simulated failure"):
            await mock.complete_async(LLMRequest(prompt="test"))
