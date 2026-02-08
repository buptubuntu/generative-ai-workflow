"""Plugin registry for LLM providers.

Central registry that maps provider names to LLMProvider instances.
The built-in OpenAI provider is pre-registered as "openai".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from generative_ai_workflow.exceptions import PluginNotFoundError, PluginRegistrationError

if TYPE_CHECKING:
    from generative_ai_workflow.providers.base import LLMProvider


class PluginRegistry:
    """Register and discover LLM provider plugins.

    The built-in OpenAI provider is pre-registered as "openai".
    Custom providers can be registered via register_provider().

    Example::

        PluginRegistry.register_provider("my_llm", MyLLMProvider)
        provider = PluginRegistry.get_provider("my_llm")
        print(PluginRegistry.list_providers())
    """

    _providers: dict[str, "LLMProvider"] = {}
    _initialized: set[str] = set()

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider: "type[LLMProvider] | LLMProvider",
    ) -> None:
        """Register a custom LLM provider.

        Args:
            name: Unique provider identifier used in workflow configuration.
            provider: LLMProvider subclass or instance to register.

        Raises:
            PluginRegistrationError: If name is already registered or
                                      provider does not implement LLMProvider.
        """
        from generative_ai_workflow.providers.base import LLMProvider as Base

        if name in cls._providers:
            raise PluginRegistrationError(
                f"Provider {name!r} is already registered. "
                "Use a different name or call unregister_provider() first."
            )

        # Accept both class and instance
        if isinstance(provider, type):
            if not issubclass(provider, Base):
                raise PluginRegistrationError(
                    f"Provider class {provider!r} must be a subclass of LLMProvider."
                )
            instance = provider()
        elif isinstance(provider, Base):
            instance = provider
        else:
            raise PluginRegistrationError(
                f"Provider must be an LLMProvider subclass or instance, got {type(provider)!r}."
            )

        cls._providers[name] = instance

    @classmethod
    def get_provider(cls, name: str) -> "LLMProvider":
        """Get an initialized LLM provider instance.

        Args:
            name: Provider identifier (as registered).

        Returns:
            Initialized LLMProvider instance.

        Raises:
            PluginNotFoundError: If provider name is not registered.
        """
        if name not in cls._providers:
            available = ", ".join(sorted(cls._providers.keys())) or "(none)"
            raise PluginNotFoundError(
                f"{name!r}. Available providers: {available}"
            )
        return cls._providers[name]

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names.

        Returns:
            Sorted list of registered provider names.
        """
        return sorted(cls._providers.keys())

    @classmethod
    def unregister_provider(cls, name: str) -> None:
        """Unregister a provider (useful for testing).

        Args:
            name: Provider identifier to remove.
        """
        cls._providers.pop(name, None)
        cls._initialized.discard(name)

    @classmethod
    def clear(cls) -> None:
        """Remove all registered providers (useful for test isolation)."""
        cls._providers.clear()
        cls._initialized.clear()
        cls._register_builtins()

    @classmethod
    def _register_builtins(cls) -> None:
        """Register built-in providers (called on module load)."""
        from generative_ai_workflow.providers.openai import OpenAIProvider
        if "openai" not in cls._providers:
            cls._providers["openai"] = OpenAIProvider()


# Register built-in providers on import
PluginRegistry._register_builtins()
