"""Unit tests for FrameworkConfig: env var loading, validation, defaults."""

from __future__ import annotations

import os

import pytest

from generative_ai_workflow import ConfigurationError, FrameworkConfig


class TestFrameworkConfigDefaults:
    """Verify sensible defaults (FR-021)."""

    def test_default_model(self) -> None:
        cfg = FrameworkConfig(openai_api_key="sk-test")
        assert cfg.default_model == "gpt-4o-mini"

    def test_default_temperature(self) -> None:
        cfg = FrameworkConfig(openai_api_key="sk-test")
        assert cfg.default_temperature == 0.7

    def test_default_max_tokens(self) -> None:
        cfg = FrameworkConfig(openai_api_key="sk-test")
        assert cfg.default_max_tokens == 1024

    def test_default_execution_mode_is_async(self) -> None:
        """FR-022: default to async execution mode."""
        cfg = FrameworkConfig(openai_api_key="sk-test")
        assert cfg.default_execution_mode == "async"

    def test_default_max_retries(self) -> None:
        cfg = FrameworkConfig(openai_api_key="sk-test")
        assert cfg.max_retry_attempts == 3


class TestFrameworkConfigValidation:
    """Verify configuration validation with clear error messages (FR-020)."""

    def test_invalid_execution_mode_raises(self) -> None:
        with pytest.raises(Exception, match="Invalid execution mode"):
            FrameworkConfig(openai_api_key="sk-test", default_execution_mode="invalid")

    def test_invalid_log_level_raises(self) -> None:
        with pytest.raises(Exception, match="Invalid log level"):
            FrameworkConfig(openai_api_key="sk-test", log_level="TRACE")

    def test_temperature_out_of_range(self) -> None:
        with pytest.raises(Exception):
            FrameworkConfig(openai_api_key="sk-test", default_temperature=3.0)

    def test_max_tokens_too_low(self) -> None:
        with pytest.raises(Exception):
            FrameworkConfig(openai_api_key="sk-test", default_max_tokens=0)


class TestFrameworkConfigEnvVars:
    """Verify env var loading (FR-019)."""

    def test_loads_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        monkeypatch.setenv("GENAI_WORKFLOW_DEFAULT_MODEL", "gpt-4")
        cfg = FrameworkConfig()
        assert cfg.openai_api_key == "sk-env-key"
        assert cfg.default_model == "gpt-4"

    def test_log_level_normalized_to_upper(self) -> None:
        cfg = FrameworkConfig(openai_api_key="sk-test", log_level="debug")
        assert cfg.log_level == "DEBUG"


class TestFromYaml:
    """Verify YAML config loading (FR-019a)."""

    def test_from_yaml_missing_file_raises_config_error(self) -> None:
        with pytest.raises(ConfigurationError, match="not found"):
            FrameworkConfig.from_yaml("/nonexistent/path/config.yaml")

    def test_from_yaml_loads_values(self, tmp_path: "Path") -> None:
        yaml_content = "default_model: gpt-4\ndefault_temperature: 0.5\n"
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        cfg = FrameworkConfig.from_yaml(str(config_file), openai_api_key="sk-test")
        assert cfg.default_model == "gpt-4"
        assert cfg.default_temperature == 0.5
