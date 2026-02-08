"""Framework configuration loaded from environment variables and optional YAML file.

All settings have sensible defaults. Only OPENAI_API_KEY is required at runtime
when using the built-in OpenAI provider.

Usage:
    >>> config = FrameworkConfig()  # loads from environment
    >>> config = FrameworkConfig(openai_api_key="sk-...")  # explicit
    >>> config = FrameworkConfig.from_yaml("config.yaml")  # YAML + env override
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrameworkConfig(BaseSettings):
    """Runtime configuration for the generative_ai_workflow framework.

    Loaded from environment variables with ``GENAI_WORKFLOW_`` prefix.
    Environment variables take precedence over YAML file values.

    Attributes:
        openai_api_key: OpenAI API key. Required when using OpenAI provider.
        default_model: Default LLM model name.
        default_temperature: Default sampling temperature.
        default_max_tokens: Default max response tokens.
        default_timeout_seconds: Default sync execution timeout (None = no limit).
        default_execution_mode: Default execution mode ("async" or "sync").
        max_retry_attempts: Max LLM API retry attempts on transient errors.
        retry_backoff_factor: Exponential backoff multiplier.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_prompts: Whether to include prompt text in structured logs.
    """

    model_config = SettingsConfigDict(
        env_prefix="GENAI_WORKFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    default_model: str = Field(default="gpt-4o-mini")
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    default_max_tokens: int = Field(default=1024, ge=1, le=128000)
    default_timeout_seconds: float | None = Field(default=None)
    default_execution_mode: str = Field(default="async")
    max_retry_attempts: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=2.0, gt=0.0)
    log_level: str = Field(default="INFO")
    log_prompts: bool = Field(default=False)

    @field_validator("default_execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        """Ensure execution mode is valid."""
        if v not in ("async", "sync"):
            raise ValueError(
                f"Invalid execution mode {v!r}. Must be 'async' or 'sync'. "
                "Set GENAI_WORKFLOW_DEFAULT_MODE=async or GENAI_WORKFLOW_DEFAULT_MODE=sync."
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(
                f"Invalid log level {v!r}. Must be one of: {', '.join(sorted(valid))}. "
                "Set GENAI_WORKFLOW_LOG_LEVEL=INFO."
            )
        return upper

    @model_validator(mode="after")
    def validate_openai_key_format(self) -> "FrameworkConfig":
        """Warn if API key looks invalid (not validating at config time, only format check)."""
        key = self.openai_api_key
        if key and not key.startswith("sk-"):
            import warnings
            warnings.warn(
                "OPENAI_API_KEY does not start with 'sk-'. "
                "Ensure a valid OpenAI API key is set.",
                stacklevel=2,
            )
        return self

    @classmethod
    def from_yaml(cls, path: str | Path, **overrides: Any) -> "FrameworkConfig":
        """Load configuration from a YAML file, with env vars taking precedence.

        Args:
            path: Path to the YAML configuration file.
            **overrides: Additional keyword overrides (highest precedence).

        Returns:
            FrameworkConfig instance.

        Raises:
            ConfigurationError: If the YAML file cannot be parsed.
        """
        import yaml
        from generative_ai_workflow.exceptions import ConfigurationError

        try:
            with open(path) as f:
                yaml_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise ConfigurationError(
                f"Configuration file not found: {path}. "
                "Create the file or omit it to use environment variables only."
            )
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Failed to parse YAML configuration file {path}: {e}. "
                "Ensure the file contains valid YAML."
            )

        # Merge: YAML < env vars < explicit overrides (pydantic-settings handles env priority)
        merged = {**yaml_data, **overrides}
        return cls(**merged)
