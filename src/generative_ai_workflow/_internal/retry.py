"""Tenacity retry configuration for LLM API calls.

Defines retry strategies with exponential backoff for transient LLM errors.
Non-retryable errors (auth, invalid request) are re-raised immediately.
"""

from __future__ import annotations

from typing import Any

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


def is_retryable_error(exc: BaseException) -> bool:
    """Determine if an exception should trigger a retry.

    Retryable: timeouts, rate limits (429), transient server errors (5xx).
    Non-retryable: authentication (401/403), invalid requests (400).

    Args:
        exc: The exception to evaluate.

    Returns:
        True if the call should be retried.
    """
    # OpenAI SDK exception types
    try:
        import openai
        if isinstance(exc, openai.RateLimitError):
            return True
        if isinstance(exc, openai.APITimeoutError):
            return True
        if isinstance(exc, openai.InternalServerError):
            return True
        if isinstance(exc, openai.APIConnectionError):
            return True
        # Auth and invalid request are non-retryable
        if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
            return False
        if isinstance(exc, openai.BadRequestError):
            return False
    except ImportError:
        pass

    # Generic HTTP status-based check
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        if status_code == 429:
            return True
        if status_code >= 500:
            return True
        if status_code in (400, 401, 403):
            return False

    return False


def build_retry(max_attempts: int = 3, backoff_factor: float = 2.0) -> AsyncRetrying:
    """Build an AsyncRetrying instance with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including first try).
        backoff_factor: Multiplier for exponential backoff.

    Returns:
        Configured AsyncRetrying instance.

    Example::

        retry = build_retry(max_attempts=3, backoff_factor=2.0)
        async for attempt in retry:
            with attempt:
                response = await provider.complete_async(request)
    """
    return AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=backoff_factor, min=1, max=60),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
