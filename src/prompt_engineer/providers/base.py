"""
Base provider interface for LLM integrations.

Defines the abstract interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Iterator
from dataclasses import dataclass
from enum import Enum


class MessageRole(str, Enum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


@dataclass
class Message:
    """A message in a conversation."""
    role: MessageRole
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        """Convert message to dictionary format."""
        result = {
            "role": self.role.value,
            "content": self.content
        }
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class ModelInfo:
    """Information about an available model."""
    id: str
    name: Optional[str] = None
    context_length: Optional[int] = None
    description: Optional[str] = None

    def __str__(self) -> str:
        return self.name or self.id


@dataclass
class LLMRequest:
    """Request parameters for LLM completion."""
    messages: List[Message]
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    stream: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary format."""
        result = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in self.messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": self.stream
        }

        if self.top_p is not None:
            result["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            result["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            result["presence_penalty"] = self.presence_penalty
        if self.stop:
            result["stop"] = self.stop

        return result


@dataclass
class LLMResponse:
    """Response from LLM completion."""
    content: str
    model: str
    finish_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def usage(self) -> Dict[str, int]:
        """Get token usage information."""
        return {
            "prompt_tokens": self.prompt_tokens or 0,
            "completion_tokens": self.completion_tokens or 0,
            "total_tokens": self.total_tokens or 0
        }


@dataclass
class StreamChunk:
    """A chunk from a streaming response."""
    content: str
    finish_reason: Optional[str] = None
    model: Optional[str] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All provider implementations must inherit from this class and implement
    the required methods.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        """
        Initialize the provider.

        Args:
            api_key: API key for authentication (may be None for local providers)
            base_url: Custom base URL for the API
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key or "not-needed"
        self.base_url = base_url
        self.config = kwargs

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """
        List available models from the provider.

        Returns:
            List of ModelInfo objects representing available models.

        Raises:
            Exception: If the API request fails
        """
        pass

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Send a completion request to the LLM.

        Args:
            request: LLMRequest object containing the prompt and parameters

        Returns:
            LLMResponse object containing the model's response

        Raises:
            Exception: If the API request fails
        """
        pass

    @abstractmethod
    def stream_complete(self, request: LLMRequest) -> Iterator[StreamChunk]:
        """
        Send a streaming completion request to the LLM.

        Args:
            request: LLMRequest object containing the prompt and parameters

        Yields:
            StreamChunk objects as they arrive from the API

        Raises:
            Exception: If the API request fails
        """
        pass

    def validate_connection(self) -> bool:
        """
        Test the connection to the provider.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            models = self.list_models()
            return len(models) > 0
        except:
            return False

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider (e.g., 'OpenAI', 'Ollama')."""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Return whether this provider supports streaming responses."""
        pass

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}(base_url={self.base_url})"


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    pass


class AuthenticationError(ProviderError):
    """Raised when authentication fails."""
    pass


class ConnectionError(ProviderError):
    """Raised when connection to provider fails."""
    pass


class ModelNotFoundError(ProviderError):
    """Raised when requested model is not available."""
    pass


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""
    pass
