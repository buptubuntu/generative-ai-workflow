"""Structured JSON logging configuration for generative_ai_workflow.

Uses structlog with orjson renderer for high-performance JSON output.
Automatically redacts API keys and other sensitive credentials from all logs.
"""

from __future__ import annotations

import logging
import re

import structlog


# ---------------------------------------------------------------------------
# Sensitive Value Redaction
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI API keys
    re.compile(r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{16,})"),
    re.compile(r"(?i)bearer\s+([A-Za-z0-9_\-\.]{16,})"),
]

_REDACTED = "[REDACTED]"


def _redact_secrets(value: str) -> str:
    """Replace known secret patterns with [REDACTED]."""
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(_REDACTED, value)
    return value


def _redact_processor(
    logger: logging.Logger | None,
    method: str,
    event_dict: dict,  # type: ignore[type-arg]
) -> dict:  # type: ignore[type-arg]
    """structlog processor that redacts secrets from all string values."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            event_dict[key] = _redact_secrets(value)
    return event_dict


# ---------------------------------------------------------------------------
# Logger Configuration
# ---------------------------------------------------------------------------


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for JSON output with secret redaction.

    Should be called once at application startup. Safe to call multiple times.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_processor,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "generative_ai_workflow") -> structlog.BoundLogger:
    """Get a bound structlog logger.

    Args:
        name: Logger name for filtering and identification.

    Returns:
        Bound structlog logger instance.
    """
    return structlog.get_logger(name)
