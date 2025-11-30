"""Configuration management for user and workspace settings."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


# Default user config location
USER_CONFIG_DIR = Path.home() / ".prompt-engineer"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.yaml"


def get_user_config_path() -> Path:
    """Get path to user config file."""
    return USER_CONFIG_FILE


def get_workspace_config_path(workspace_root: str) -> Path:
    """Get path to workspace config file."""
    return Path(workspace_root) / ".prompt-engineer" / "workspace.yaml"


def load_user_config() -> Dict[str, Any]:
    """Load user-level configuration."""
    if not USER_CONFIG_FILE.exists():
        return get_default_user_config()

    try:
        with open(USER_CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f) or get_default_user_config()
    except Exception as e:
        print(f"Error loading user config: {e}")
        return get_default_user_config()


def save_user_config(config: Dict[str, Any]) -> str:
    """Save user-level configuration."""
    try:
        USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIG_FILE, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return f"✅ User config saved to {USER_CONFIG_FILE}"
    except Exception as e:
        return f"❌ Error saving user config: {e}"


def load_workspace_config(workspace_root: str) -> Dict[str, Any]:
    """Load workspace-level configuration."""
    config_path = get_workspace_config_path(workspace_root)

    if not config_path.exists():
        return get_default_workspace_config()

    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or get_default_workspace_config()
    except Exception as e:
        print(f"Error loading workspace config: {e}")
        return get_default_workspace_config()


def save_workspace_config(workspace_root: str, config: Dict[str, Any]) -> str:
    """Save workspace-level configuration."""
    try:
        config_path = get_workspace_config_path(workspace_root)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return f"✅ Workspace config saved to {config_path}"
    except Exception as e:
        return f"❌ Error saving workspace config: {e}"


def get_default_user_config() -> Dict[str, Any]:
    """Get default user configuration."""
    return {
        "provider": "openai",
        "api_key": "",
        "base_url": "",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "defaults": {
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 2000,
        },
        "presets": {
            "openai": {
                "base_url": "",
                "api_key_required": True,
                "default_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            },
            "ollama": {
                "base_url": "http://localhost:11434/v1",
                "api_key_required": False,
                "default_models": ["llama3.2", "mistral", "codellama"],
            },
            "lm-studio": {
                "base_url": "http://localhost:1234/v1",
                "api_key_required": False,
                "default_models": [],
            },
            "openrouter": {
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_required": True,
                "default_models": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
            },
        },
    }


def get_default_workspace_config() -> Dict[str, Any]:
    """Get default workspace configuration."""
    return {
        "name": "My Workspace",
        "paths": {
            "prompts": "prompts",
            "data": "prompt-data",
        },
        "variables": {},
        "defaults": {
            "model": "",  # Empty means use user default
            "temperature": None,  # None means use user default
        },
    }


def validate_user_config(config: Dict[str, Any]) -> List[str]:
    """Validate user config and return list of errors."""
    errors = []

    if not config.get("provider"):
        errors.append("Missing provider")

    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")

    # Check if API key is needed
    presets = config.get("presets", {})
    provider = config.get("provider", "")
    preset = presets.get(provider, {})

    if preset.get("api_key_required") and not api_key and not base_url:
        errors.append("API key or base URL required for this provider")

    if not config.get("models"):
        errors.append("No models configured")

    return errors


def validate_workspace_config(workspace_root: str, config: Dict[str, Any]) -> List[str]:
    """Validate workspace config and return list of errors."""
    errors = []

    # Check paths
    paths = config.get("paths", {})
    prompt_dir = paths.get("prompts")
    data_dir = paths.get("data")

    if not prompt_dir:
        errors.append("Missing prompt directory path")
    elif not (Path(workspace_root) / prompt_dir).exists():
        errors.append(f"Prompt directory not found: {prompt_dir}")

    if not data_dir:
        errors.append("Missing data directory path")
    elif not (Path(workspace_root) / data_dir).exists():
        errors.append(f"Data directory not found: {data_dir}")

    # Check variable files
    variables = config.get("variables", {})
    for var_name, var_config in variables.items():
        if var_config.get("type") == "file":
            file_path = var_config.get("path")
            if not file_path:
                errors.append(f"Variable '{var_name}': missing file path")
            else:
                full_path = Path(workspace_root) / file_path
                if not full_path.exists():
                    errors.append(f"Variable '{var_name}': file not found: {file_path}")

    return errors
