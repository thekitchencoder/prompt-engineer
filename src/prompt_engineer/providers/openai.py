"""
OpenAI-compatible provider implementation.

Supports OpenAI API and any OpenAI-compatible endpoints (Ollama, LM Studio, etc.).
"""

from typing import List, Optional, Iterator, Dict, Any
from openai import OpenAI
from .base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    StreamChunk,
    ModelInfo,
    Message,
    MessageRole,
    ProviderError,
    AuthenticationError,
    ConnectionError,
    ModelNotFoundError,
    RateLimitError
)
import re


class OpenAIProvider(LLMProvider):
    """
    Provider implementation for OpenAI and OpenAI-compatible APIs.

    Supports:
    - OpenAI (api.openai.com)
    - Ollama (localhost:11434)
    - LM Studio (localhost:1234)
    - OpenRouter (openrouter.ai)
    - vLLM
    - Any other OpenAI-compatible API
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        """
        Initialize OpenAI provider.

        Args:
            api_key: API key (use "not-needed" for local providers)
            base_url: Custom base URL (None for OpenAI default)
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, base_url, **kwargs)

        # Initialize OpenAI client
        if self.base_url:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = OpenAI(api_key=self.api_key)

    def list_models(self) -> List[ModelInfo]:
        """
        List available models from the API.

        Returns:
            List of ModelInfo objects

        Raises:
            ConnectionError: If unable to connect to API
            AuthenticationError: If API key is invalid
            ProviderError: For other API errors
        """
        try:
            response = self.client.models.list()
            models = []

            for model in response.data:
                models.append(ModelInfo(
                    id=model.id,
                    name=model.id,
                    description=getattr(model, 'description', None)
                ))

            # Sort models alphabetically
            models.sort(key=lambda m: m.id)
            return models

        except Exception as e:
            error_msg = str(e).lower()

            if "connection" in error_msg or "connect" in error_msg:
                raise ConnectionError(f"Unable to connect to {self.base_url or 'OpenAI API'}: {e}")
            elif "401" in error_msg or "unauthorized" in error_msg:
                raise AuthenticationError(f"Invalid API key: {e}")
            elif "403" in error_msg or "forbidden" in error_msg:
                raise AuthenticationError(f"Access forbidden - check API key permissions: {e}")
            elif "429" in error_msg or "rate limit" in error_msg:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            else:
                raise ProviderError(f"Error listing models: {e}")

    def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Send a completion request to the API.

        Args:
            request: LLMRequest object with prompt and parameters

        Returns:
            LLMResponse object with the model's response

        Raises:
            ModelNotFoundError: If model is not available
            ProviderError: For other API errors
        """
        try:
            # Convert request to API format
            api_request = request.to_dict()

            # Make API call
            response = self.client.chat.completions.create(**api_request)

            # Extract response data
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Extract token usage if available
            usage = getattr(response, 'usage', None)
            prompt_tokens = getattr(usage, 'prompt_tokens', None) if usage else None
            completion_tokens = getattr(usage, 'completion_tokens', None) if usage else None
            total_tokens = getattr(usage, 'total_tokens', None) if usage else None

            # Process thinking tags for reasoning models
            processed_content = self._process_thinking_tags(content)

            return LLMResponse(
                content=processed_content,
                model=response.model,
                finish_reason=finish_reason,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                raw_response=response.model_dump()
            )

        except Exception as e:
            error_msg = str(e).lower()

            if "model" in error_msg and ("not found" in error_msg or "does not exist" in error_msg):
                raise ModelNotFoundError(f"Model '{request.model}' not found: {e}")
            elif "429" in error_msg or "rate limit" in error_msg:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            else:
                raise ProviderError(f"Error calling API: {e}")

    def stream_complete(self, request: LLMRequest) -> Iterator[StreamChunk]:
        """
        Send a streaming completion request to the API.

        Args:
            request: LLMRequest object with prompt and parameters

        Yields:
            StreamChunk objects as they arrive

        Raises:
            ModelNotFoundError: If model is not available
            ProviderError: For other API errors
        """
        try:
            # Convert request to API format and enable streaming
            api_request = request.to_dict()
            api_request["stream"] = True

            # Make streaming API call
            stream = self.client.chat.completions.create(**api_request)

            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, 'content', None)
                    finish_reason = chunk.choices[0].finish_reason

                    if content:
                        yield StreamChunk(
                            content=content,
                            finish_reason=finish_reason,
                            model=chunk.model
                        )

        except Exception as e:
            error_msg = str(e).lower()

            if "model" in error_msg and ("not found" in error_msg or "does not exist" in error_msg):
                raise ModelNotFoundError(f"Model '{request.model}' not found: {e}")
            elif "429" in error_msg or "rate limit" in error_msg:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            else:
                raise ProviderError(f"Error streaming from API: {e}")

    def _process_thinking_tags(self, content: str) -> str:
        """
        Process <think>...</think> tags from reasoning models.

        Args:
            content: Raw content from the model

        Returns:
            Formatted content with thinking sections highlighted
        """
        if not content:
            return content

        # Check if response contains thinking tags
        think_pattern = r'<think>(.*?)</think>'
        thinks = re.findall(think_pattern, content, re.DOTALL)

        if not thinks:
            # No thinking tags, return as-is
            return content

        # Remove thinking tags from content
        response_without_think = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()

        # Format thinking sections
        formatted_thinks = []
        for i, think in enumerate(thinks, 1):
            think_text = think.strip()
            formatted_thinks.append(f"**🤔 Thinking ({i}):**\n```\n{think_text}\n```\n")

        # Combine: thinking sections first, then response
        if formatted_thinks:
            thinking_section = "\n".join(formatted_thinks)
            if response_without_think:
                return f"{thinking_section}\n---\n\n{response_without_think}"
            else:
                return thinking_section

        return response_without_think if response_without_think else content

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        if self.base_url:
            if "ollama" in self.base_url.lower():
                return "Ollama"
            elif "lmstudio" in self.base_url.lower() or "localhost:1234" in self.base_url:
                return "LM Studio"
            elif "openrouter" in self.base_url.lower():
                return "OpenRouter"
            elif "vllm" in self.base_url.lower() or "localhost:8000" in self.base_url:
                return "vLLM"
            else:
                return "Custom OpenAI-compatible"
        else:
            return "OpenAI"

    @property
    def supports_streaming(self) -> bool:
        """Return whether streaming is supported."""
        return True

    def simple_complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Simplified completion method for basic use cases.

        Args:
            prompt: User prompt text
            model: Model ID to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            String response from the model
        """
        request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content=prompt)],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        response = self.complete(request)
        return response.content

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Complete a multi-turn conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model ID to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            String response from the model
        """
        msg_objects = [
            Message(
                role=MessageRole(msg["role"]),
                content=msg["content"]
            )
            for msg in messages
        ]

        request = LLMRequest(
            messages=msg_objects,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        response = self.complete(request)
        return response.content
