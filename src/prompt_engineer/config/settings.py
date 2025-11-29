"""
Configuration management for Prompt Engineer.

Handles provider presets, environment configuration, and application settings
using Pydantic for type safety and validation.
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from pathlib import Path
import os


class ProviderPreset(BaseModel):
    """Configuration preset for an LLM provider."""

    base_url: str = Field(default="", description="API base URL (empty for OpenAI)")
    api_key_required: bool = Field(default=True, description="Whether API key is required")
    default_models: str = Field(default="", description="Comma-separated list of default models")
    api_key_placeholder: str = Field(default="your-api-key", description="Placeholder text for API key input")

    def get_models_list(self) -> List[str]:
        """Convert comma-separated models string to list."""
        if not self.default_models:
            return []
        return [model.strip() for model in self.default_models.split(",") if model.strip()]


class ProviderPresets:
    """Collection of provider presets."""

    OPENAI = ProviderPreset(
        base_url="",
        api_key_required=True,
        default_models="gpt-4o,gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo",
        api_key_placeholder="sk-..."
    )

    OLLAMA = ProviderPreset(
        base_url="http://localhost:11434/v1",
        api_key_required=False,
        default_models="llama3.2,mistral,codellama,phi3",
        api_key_placeholder="not-needed"
    )

    LM_STUDIO = ProviderPreset(
        base_url="http://localhost:1234/v1",
        api_key_required=False,
        default_models="",
        api_key_placeholder="not-needed"
    )

    OPENROUTER = ProviderPreset(
        base_url="https://openrouter.ai/api/v1",
        api_key_required=True,
        default_models="anthropic/claude-3.5-sonnet,openai/gpt-4o,meta-llama/llama-3.2-90b",
        api_key_placeholder="sk-or-v1-..."
    )

    VLLM = ProviderPreset(
        base_url="http://localhost:8000/v1",
        api_key_required=False,
        default_models="",
        api_key_placeholder="not-needed"
    )

    CUSTOM = ProviderPreset(
        base_url="",
        api_key_required=True,
        default_models="",
        api_key_placeholder="your-api-key"
    )

    @classmethod
    def get_preset(cls, name: str) -> ProviderPreset:
        """Get provider preset by name."""
        presets = {
            "OpenAI": cls.OPENAI,
            "Ollama": cls.OLLAMA,
            "LM Studio": cls.LM_STUDIO,
            "OpenRouter": cls.OPENROUTER,
            "vLLM": cls.VLLM,
            "Custom": cls.CUSTOM
        }
        return presets.get(name, cls.CUSTOM)

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Get list of all provider preset names."""
        return ["OpenAI", "Ollama", "LM Studio", "OpenRouter", "vLLM", "Custom"]


class ModelSettings(BaseModel):
    """Settings for model inference parameters."""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, le=32000, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Presence penalty")


class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.

    These settings are persisted to .env file and loaded on startup.
    """

    # Provider configuration
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY", description="API key for OpenAI or compatible API")
    openai_base_url: str = Field(default="", env="OPENAI_BASE_URL", description="Base URL for API (empty for OpenAI)")
    provider_name: str = Field(default="OpenAI", env="PROVIDER_NAME", description="Display name of provider")

    # Available models
    available_models: str = Field(default="", env="AVAILABLE_MODELS", description="Comma-separated list of models")
    default_model: str = Field(default="", env="DEFAULT_MODEL", description="Default model to use")

    # Model defaults
    default_temperature: float = Field(default=0.7, env="DEFAULT_TEMPERATURE", description="Default temperature")
    default_max_tokens: int = Field(default=1000, env="DEFAULT_MAX_TOKENS", description="Default max tokens")

    # Application settings
    templates_dir: Path = Field(default=Path("templates"), description="Directory for saved templates")
    variables_dir: Path = Field(default=Path("variables"), description="Directory for variable files")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_models_list(self) -> List[str]:
        """Get list of available models."""
        if not self.available_models:
            return []
        return [model.strip() for model in self.available_models.split(",") if model.strip()]

    def get_api_key_or_default(self) -> str:
        """Get API key or return 'not-needed' for local providers."""
        return self.openai_api_key or "not-needed"

    def get_base_url_or_none(self) -> Optional[str]:
        """Get base URL or None (for OpenAI default)."""
        return self.openai_base_url if self.openai_base_url else None

    def needs_configuration(self) -> bool:
        """Check if the app needs initial configuration."""
        return not self.openai_api_key and not self.openai_base_url

    def to_dict(self) -> Dict:
        """Convert settings to dictionary."""
        return {
            "api_key": self.openai_api_key,
            "base_url": self.openai_base_url,
            "provider_name": self.provider_name,
            "models": self.available_models,
            "default_model": self.default_model,
            "temperature": self.default_temperature,
            "max_tokens": self.default_max_tokens
        }


class ConfigManager:
    """
    Manages application configuration including providers, models, and settings.

    Handles loading from .env, updating configuration, and saving changes.
    """

    def __init__(self, env_file: str = ".env"):
        self.env_file = Path(env_file)
        self.settings = AppSettings(_env_file=str(self.env_file))
        self.presets = ProviderPresets()

    def save_to_env(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider_name: Optional[str] = None,
        models: Optional[str] = None,
        default_model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> bool:
        """
        Save configuration to .env file.

        Returns True if successful, False otherwise.
        """
        from dotenv import set_key, find_dotenv

        # Create .env if it doesn't exist
        if not self.env_file.exists():
            self.env_file.touch()

        env_path = str(self.env_file)

        try:
            if api_key is not None:
                set_key(env_path, "OPENAI_API_KEY", api_key or "not-needed")
                self.settings.openai_api_key = api_key or "not-needed"

            if base_url is not None:
                set_key(env_path, "OPENAI_BASE_URL", base_url or "")
                self.settings.openai_base_url = base_url or ""

            if provider_name is not None:
                set_key(env_path, "PROVIDER_NAME", provider_name)
                self.settings.provider_name = provider_name

            if models is not None:
                set_key(env_path, "AVAILABLE_MODELS", models)
                self.settings.available_models = models

            if default_model is not None:
                set_key(env_path, "DEFAULT_MODEL", default_model)
                self.settings.default_model = default_model

            if temperature is not None:
                set_key(env_path, "DEFAULT_TEMPERATURE", str(temperature))
                self.settings.default_temperature = temperature

            if max_tokens is not None:
                set_key(env_path, "DEFAULT_MAX_TOKENS", str(max_tokens))
                self.settings.default_max_tokens = max_tokens

            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

    def get_provider_preset(self, provider_name: str) -> ProviderPreset:
        """Get provider preset by name."""
        return self.presets.get_preset(provider_name)

    def get_all_provider_names(self) -> List[str]:
        """Get list of all provider names."""
        return self.presets.get_all_names()

    def reload(self):
        """Reload settings from .env file."""
        self.settings = AppSettings(_env_file=str(self.env_file))
