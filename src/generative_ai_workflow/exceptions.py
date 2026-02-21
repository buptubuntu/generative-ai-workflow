"""Exception hierarchy for generative_ai_workflow.

All framework exceptions inherit from FrameworkError, allowing callers
to catch the base class to handle any framework-raised exception.
"""

from __future__ import annotations


class FrameworkError(Exception):
    """Base class for all framework exceptions."""


class ProviderError(FrameworkError):
    """LLM provider call failed (after retries exhausted)."""


class ProviderAuthError(ProviderError):
    """LLM provider authentication failed (non-retryable)."""


class NodeError(FrameworkError):
    """Workflow node execution failed.

    Attributes:
        node_name: Name of the node that failed.
    """

    def __init__(self, message: str, node_name: str = "") -> None:
        super().__init__(message)
        self.node_name = node_name


class WorkflowError(FrameworkError):
    """General workflow execution error."""


class PluginError(FrameworkError):
    """Plugin operation failed."""


class PluginNotFoundError(PluginError):
    """Requested plugin is not registered.

    Attributes:
        plugin_name: Name of the unregistered plugin.
    """

    def __init__(self, plugin_name: str) -> None:
        super().__init__(f"Plugin not found: {plugin_name!r}")
        self.plugin_name = plugin_name


class PluginRegistrationError(PluginError):
    """Plugin registration failed (duplicate name or invalid class)."""


class AbortError(FrameworkError):
    """Raised by middleware to short-circuit LLM call execution."""


class ConfigurationError(FrameworkError):
    """Framework configuration is invalid or missing required values."""
