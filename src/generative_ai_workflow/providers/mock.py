"""MockLLMProvider for testing without real API calls.

Provides configurable canned responses with simulated token usage.
Supports both sync and async execution modes.
"""

from __future__ import annotations

from typing import Any

from generative_ai_workflow.providers.base import LLMProvider, LLMRequest, LLMResponse, TokenUsage


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for zero-cost testing.

    Returns canned responses instead of making real API calls.
    Simulates token usage based on response length.

    Args:
        responses: Dict mapping lookup key to response content.
                   Use "default" for a catch-all response.
        fail_with: If set, all calls raise this exception (for error testing).

    Example::

        mock = MockLLMProvider(responses={"default": "Mock response text."})
        PluginRegistry.register_provider("mock", mock)

        # Zero-cost test
        result = await workflow.execute_async({"text": "anything"})
        assert result.status == "completed"
    """

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        fail_with: Exception | None = None,
    ) -> None:
        self._responses = responses or {"default": "Mock LLM response."}
        self._fail_with = fail_with
        self._call_count = 0
        self._call_log: list[LLMRequest] = []

    async def complete_async(self, request: LLMRequest) -> LLMResponse:
        """Return a canned response for the request.

        Args:
            request: The LLM request specification.

        Returns:
            LLMResponse with canned content and simulated token usage.

        Raises:
            Exception: If fail_with was set during construction.
        """
        self._call_count += 1
        self._call_log.append(request)

        if self._fail_with is not None:
            raise self._fail_with

        content = self._responses.get(request.prompt, self._responses.get("default", ""))

        # Simulate token counts based on text length (rough approximation)
        prompt_tokens = max(1, len(request.prompt) // 4)
        completion_tokens = max(1, len(content) // 4)

        return LLMResponse(
            content=content,
            model=request.model,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                model=request.model,
                provider="mock",
            ),
            latency_ms=0.1,  # simulate near-instant response
            finish_reason="stop",
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a canned response synchronously (no event loop needed).

        Args:
            request: The LLM request specification.

        Returns:
            LLMResponse with canned content.
        """
        import asyncio
        return asyncio.run(self.complete_async(request))

    @property
    def call_count(self) -> int:
        """Number of times complete_async was called."""
        return self._call_count

    @property
    def call_log(self) -> list[LLMRequest]:
        """List of all requests received."""
        return list(self._call_log)

    def reset(self) -> None:
        """Reset call count and log."""
        self._call_count = 0
        self._call_log.clear()
