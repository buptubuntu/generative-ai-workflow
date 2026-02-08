"""Unit tests for structured logging: JSON output, redaction, correlation IDs."""

from __future__ import annotations

import json
import re
from io import StringIO

import pytest
import structlog

from generative_ai_workflow.observability.logging import (
    _redact_secrets,
    configure_logging,
    get_logger,
)


class TestSecretRedaction:
    """Verify API keys are never logged (FR-027)."""

    def test_redacts_openai_key(self) -> None:
        result = _redact_secrets("key=sk-abcdefghijklmnopqrstuvwxyz1234567890")
        assert "sk-" not in result
        assert "[REDACTED]" in result

    def test_leaves_safe_strings_intact(self) -> None:
        result = _redact_secrets("Hello, world!")
        assert result == "Hello, world!"

    def test_redacts_bearer_token(self) -> None:
        result = _redact_secrets("Authorization: bearer myverylongsecrettoken123")
        assert "myverylongsecrettoken123" not in result


class TestStructuredLogging:
    """Verify structlog outputs valid JSON."""

    def test_configure_logging_does_not_raise(self) -> None:
        configure_logging("INFO")  # no exception

    def test_get_logger_returns_logger(self) -> None:
        logger = get_logger("test")
        assert logger is not None

    def test_log_output_is_valid_json(self, capsys) -> None:
        configure_logging("DEBUG")
        logger = get_logger("test")
        logger.info("test_event", key="value", count=42)
        captured = capsys.readouterr()
        # Find the JSON line
        for line in captured.out.splitlines():
            if "test_event" in line:
                parsed = json.loads(line)
                assert parsed["event"] == "test_event"
                assert parsed["key"] == "value"
                assert parsed["count"] == 42
                break
        else:
            pytest.fail("Expected JSON log line not found")
