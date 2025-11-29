"""
Provider registry and factory for creating LLM provider instances.

Provides a centralized way to create and manage provider instances.
"""

from typing import Dict, Type, Optional, List
from .base import LLMProvider
from .openai import OpenAIProvider


class ProviderRegistry:
    """
    Registry for LLM provider implementations.

    Manages provider types and creates instances based on configuration.
    """

    def __init__(self):
        """Initialize the provider registry."""
        self._providers: Dict[str, Type[LLMProvider]] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        """Register built-in provider implementations."""
        # All OpenAI-compatible providers use the same implementation
        self.register("openai", OpenAIProvider)
        self.register("ollama", OpenAIProvider)
        self.register("lm_studio", OpenAIProvider)
        self.register("openrouter", OpenAIProvider)
        self.register("vllm", OpenAIProvider)
        self.register("custom", OpenAIProvider)

    def register(self, name: str, provider_class: Type[LLMProvider]):
        """
        Register a provider implementation.

        Args:
            name: Unique name for the provider (lowercase, snake_case)
            provider_class: Provider class that inherits from LLMProvider
        """
        if not issubclass(provider_class, LLMProvider):
            raise ValueError(f"Provider class must inherit from LLMProvider")

        self._providers[name.lower()] = provider_class

    def unregister(self, name: str):
        """
        Unregister a provider.

        Args:
            name: Name of the provider to unregister
        """
        if name.lower() in self._providers:
            del self._providers[name.lower()]

    def get_provider_class(self, name: str) -> Optional[Type[LLMProvider]]:
        """
        Get provider class by name.

        Args:
            name: Provider name

        Returns:
            Provider class or None if not found
        """
        return self._providers.get(name.lower())

    def create_provider(
        self,
        provider_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """
        Create a provider instance.

        Args:
            provider_name: Name of the provider (e.g., "openai", "ollama")
            api_key: API key for authentication
            base_url: Custom base URL
            **kwargs: Additional provider-specific configuration

        Returns:
            Configured provider instance

        Raises:
            ValueError: If provider name is not registered
        """
        # Normalize provider name
        normalized_name = self._normalize_provider_name(provider_name)

        provider_class = self.get_provider_class(normalized_name)
        if not provider_class:
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {', '.join(self.list_providers())}"
            )

        return provider_class(api_key=api_key, base_url=base_url, **kwargs)

    def _normalize_provider_name(self, name: str) -> str:
        """
        Normalize provider name to registry key format.

        Args:
            name: Provider name (e.g., "OpenAI", "LM Studio")

        Returns:
            Normalized name (e.g., "openai", "lm_studio")
        """
        # Convert to lowercase and replace spaces with underscores
        normalized = name.lower().replace(" ", "_").replace("-", "_")

        # Handle common variations
        if "lmstudio" in normalized or "lm_studio" in normalized:
            return "lm_studio"
        elif "openrouter" in normalized:
            return "openrouter"
        elif "vllm" in normalized:
            return "vllm"

        return normalized

    def list_providers(self) -> List[str]:
        """
        List all registered provider names.

        Returns:
            List of provider names
        """
        return sorted(self._providers.keys())

    def is_registered(self, name: str) -> bool:
        """
        Check if a provider is registered.

        Args:
            name: Provider name

        Returns:
            True if registered, False otherwise
        """
        return name.lower() in self._providers


# Global provider registry instance
_global_registry = ProviderRegistry()


def get_provider_registry() -> ProviderRegistry:
    """
    Get the global provider registry.

    Returns:
        Global ProviderRegistry instance
    """
    return _global_registry


def create_provider(
    provider_name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    Convenience function to create a provider using the global registry.

    Args:
        provider_name: Name of the provider
        api_key: API key for authentication
        base_url: Custom base URL
        **kwargs: Additional configuration

    Returns:
        Configured provider instance
    """
    return _global_registry.create_provider(
        provider_name=provider_name,
        api_key=api_key,
        base_url=base_url,
        **kwargs
    )


def register_provider(name: str, provider_class: Type[LLMProvider]):
    """
    Convenience function to register a provider in the global registry.

    Args:
        name: Provider name
        provider_class: Provider class
    """
    _global_registry.register(name, provider_class)


def list_available_providers() -> List[str]:
    """
    List all available providers.

    Returns:
        List of provider names
    """
    return _global_registry.list_providers()
