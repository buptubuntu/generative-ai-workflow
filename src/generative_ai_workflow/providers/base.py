"""LLM provider base models and abstract interface.

Defines the data models shared by all providers (TokenUsage, LLMRequest, LLMResponse)
and the LLMProvider ABC that custom providers must implement.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class TokenUsage(BaseModel):
    """Token consumption record for a single LLM operation.

    Attributes:
        prompt_tokens: Tokens consumed by the input prompt.
        completion_tokens: Tokens in the generated response.
        total_tokens: Sum of prompt and completion tokens (validated).
        model: Model name used for this operation.
        provider: Provider name (e.g., "openai").
    """

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    model: str = Field(min_length=1)
    provider: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_total(self) -> "TokenUsage":
        """Ensure total_tokens == prompt_tokens + completion_tokens."""
        expected = self.prompt_tokens + self.completion_tokens
        if self.total_tokens != expected:
            raise ValueError(
                f"total_tokens ({self.total_tokens}) must equal "
                f"prompt_tokens + completion_tokens ({expected})"
            )
        return self


class LLMRequest(BaseModel):
    """Input specification for an LLM completion call.

    Attributes:
        prompt: The user prompt text.
        model: LLM model name. Defaults to "gpt-4o-mini".
        temperature: Sampling temperature [0.0, 2.0]. Defaults to 0.7.
        max_tokens: Maximum response tokens [1, 128000]. Defaults to 1024.
        system_prompt: Optional system message.
        extra_params: Provider-specific passthrough parameters.
    """

    prompt: str = Field(min_length=1)
    model: str = Field(default="gpt-4o-mini", min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=128000)
    system_prompt: str | None = Field(default=None)
    extra_params: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Output from an LLM completion call.

    Attributes:
        content: Generated text content.
        model: Actual model used (may differ from request if aliased).
        usage: Token consumption details.
        latency_ms: Total provider round-trip time in milliseconds.
        finish_reason: Completion reason (e.g., "stop", "length", "error").
    """

    content: str
    model: str = Field(min_length=1)
    usage: TokenUsage
    latency_ms: float = Field(ge=0.0)
    finish_reason: str = Field(default="stop")


# ---------------------------------------------------------------------------
# PII Detection Utilities (FR-030)
# ---------------------------------------------------------------------------

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}


def detect_pii(text: str) -> dict[str, list[str]]:
    """Detect common PII patterns in text.

    Args:
        text: Input text to scan.

    Returns:
        Dictionary mapping PII type to list of found matches.
        Empty dict if no PII detected.

    Example:
        >>> results = detect_pii("Contact me at user@example.com")
        >>> results["email"]
        ['user@example.com']
    """
    found: dict[str, list[str]] = {}
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found[pii_type] = matches
    return found


# ---------------------------------------------------------------------------
# LLMProvider ABC (Extension Point 1)
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """Abstract base class for LLM provider integrations.

    Implement this interface to add custom LLM providers without modifying
    framework code. The built-in OpenAIProvider implements this as a
    first-party plugin.

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

        Default implementation wraps complete_async in an event loop.
        Override for providers with native sync implementations.

        Args:
            request: The LLM request specification.

        Returns:
            LLMResponse with content, token usage, and metadata.
        """
        import asyncio
        return asyncio.run(self.complete_async(request))

    async def initialize(self) -> None:
        """Initialize provider resources (connections, credentials).

        Called once before first use. Override for providers requiring
        setup such as connection pooling or credential validation.
        """

    async def cleanup(self) -> None:
        """Release provider resources.

        Called on framework shutdown. Override for providers requiring
        cleanup such as closing connections or releasing locks.
        """
