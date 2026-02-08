"""Built-in OpenAI LLM provider.

Uses the AsyncOpenAI client with tenacity retry and exponential backoff.
Captures full token usage and metadata from each API response.
"""

from __future__ import annotations

import time
from typing import Any

from generative_ai_workflow.exceptions import ProviderAuthError, ProviderError
from generative_ai_workflow.observability.logging import get_logger
from generative_ai_workflow.providers.base import LLMProvider, LLMRequest, LLMResponse, TokenUsage

logger = get_logger("generative_ai_workflow.providers.openai")


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider using AsyncOpenAI client.

    Implements exponential backoff retry for transient errors (429/5xx).
    Captures token usage from API response for cost tracking.

    Args:
        api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        max_retries: Maximum retry attempts. Defaults to 3.
        backoff_factor: Exponential backoff multiplier. Defaults to 2.0.
        http_client: Optional custom httpx AsyncClient (for testing with respx).

    Example::

        provider = OpenAIProvider(api_key="sk-...")
        response = await provider.complete_async(
            LLMRequest(prompt="Hello, world!", model="gpt-4o-mini")
        )
        print(response.usage.total_tokens)
    """

    def __init__(
        self,
        api_key: str | None = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        http_client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._http_client = http_client
        self._client: Any | None = None

    async def initialize(self) -> None:
        """Initialize the AsyncOpenAI client."""
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._http_client is not None:
            kwargs["http_client"] = self._http_client

        self._client = AsyncOpenAI(**kwargs)

    async def cleanup(self) -> None:
        """Close the AsyncOpenAI client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion using the OpenAI API with retry.

        Args:
            request: The LLM request specification.

        Returns:
            LLMResponse with content, token usage, and metadata.

        Raises:
            ProviderAuthError: If authentication fails (non-retryable).
            ProviderError: If all retry attempts fail.
        """
        if self._client is None:
            await self.initialize()

        from generative_ai_workflow._internal.retry import build_retry

        retry = build_retry(
            max_attempts=self._max_retries,
            backoff_factor=self._backoff_factor,
        )

        try:
            async for attempt in retry:
                with attempt:
                    return await self._call_api(request)
        except Exception as e:
            self._handle_error(e)
            raise  # unreachable, but satisfies type checker

        # Should never reach here
        raise ProviderError("Retry loop exited without result or error")

    async def _call_api(self, request: LLMRequest) -> LLMResponse:
        """Make a single API call to OpenAI."""
        start = time.perf_counter()

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        logger.debug(
            "openai.request",
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            prompt_length=len(request.prompt),
        )

        response = await self._client.chat.completions.create(  # type: ignore[union-attr]
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            **request.extra_params,
        )

        latency_ms = (time.perf_counter() - start) * 1000
        content = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason or "stop"
        usage = response.usage

        token_usage = TokenUsage(
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=response.model,
            provider="openai",
        )

        logger.debug(
            "openai.response",
            model=response.model,
            finish_reason=finish_reason,
            latency_ms=round(latency_ms, 2),
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            total_tokens=token_usage.total_tokens,
        )

        return LLMResponse(
            content=content,
            model=response.model,
            usage=token_usage,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
        )

    def _handle_error(self, exc: Exception) -> None:
        """Convert OpenAI SDK exceptions to framework exceptions."""
        try:
            import openai
            if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
                raise ProviderAuthError(
                    f"OpenAI authentication failed: {exc}. "
                    "Check that OPENAI_API_KEY is valid."
                ) from exc
        except ImportError:
            pass

        raise ProviderError(
            f"OpenAI API call failed after {self._max_retries} attempts: {exc}"
        ) from exc
