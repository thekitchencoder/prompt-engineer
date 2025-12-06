"""Unit tests for config.py."""

import pytest
import yaml
from pathlib import Path
from prompt_engineer import config


class TestUserConfig:
    """Tests for user-level configuration."""

    def test_get_default_user_config(self):
        """Test default user config structure."""
        default = config.get_default_user_config()

        assert "provider" in default
        assert "api_key" in default
        assert "base_url" in default
        assert "models" in default
        assert "defaults" in default
        assert "presets" in default

        # Check presets exist
        assert "openai" in default["presets"]
        assert "ollama" in default["presets"]
        assert "lm-studio" in default["presets"]
        assert "openrouter" in default["presets"]

    def test_load_user_config_nonexistent(self, temp_user_config_dir):
        """Test loading config when file doesn't exist returns defaults."""
        loaded = config.load_user_config()
        default = config.get_default_user_config()

        assert loaded == default

    def test_save_and_load_user_config(self, temp_user_config_dir):
        """Test saving and loading user config."""
        test_config = config.get_default_user_config()
        test_config["api_key"] = "test-key-123"
        test_config["provider"] = "ollama"

        # Save config
        result = config.save_user_config(test_config)
        assert "✅" in result

        # Load and verify
        loaded = config.load_user_config()
        assert loaded["api_key"] == "test-key-123"
        assert loaded["provider"] == "ollama"

    def test_validate_user_config_valid(self):
        """Test validation of valid user config."""
        valid_config = {
            "provider": "openai",
            "api_key": "sk-test",
            "models": ["gpt-4o"],
            "presets": config.get_default_user_config()["presets"]
        }

        errors = config.validate_user_config(valid_config)
        assert len(errors) == 0

    def test_validate_user_config_missing_provider(self):
        """Test validation catches missing provider."""
        invalid_config = {
            "api_key": "test",
            "models": ["gpt-4o"]
        }

        errors = config.validate_user_config(invalid_config)
        assert any("provider" in err.lower() for err in errors)

    def test_validate_user_config_missing_models(self):
        """Test validation catches missing models."""
        invalid_config = {
            "provider": "openai",
            "api_key": "test",
            "models": []
        }

        errors = config.validate_user_config(invalid_config)
        assert any("model" in err.lower() for err in errors)

    def test_validate_user_config_missing_api_key(self):
        """Test validation catches missing API key for providers that require it."""
        invalid_config = {
            "provider": "openai",
            "api_key": "",
            "base_url": "",
            "models": ["gpt-4o"],
            "presets": config.get_default_user_config()["presets"]
        }

        errors = config.validate_user_config(invalid_config)
        assert any("api key" in err.lower() or "required" in err.lower() for err in errors)


class TestWorkspaceConfig:
    """Tests for workspace-level configuration."""

    def test_get_default_workspace_config(self):
        """Test default workspace config structure."""
        default = config.get_default_workspace_config()

        assert "paths" in default
        assert "prompts" in default["paths"]
        assert "variables" in default
        assert "defaults" in default

    def test_get_workspace_config_path(self, temp_workspace):
        """Test workspace config path construction."""
        path = config.get_workspace_config_path(temp_workspace)

        expected = Path(temp_workspace) / ".prompt-engineer" / "workspace.yaml"
        assert path == expected

    def test_load_workspace_config_nonexistent(self, temp_workspace):
        """Test loading workspace config when file doesn't exist returns defaults."""
        loaded = config.load_workspace_config(temp_workspace)
        default = config.get_default_workspace_config()

        assert loaded == default

    def test_save_and_load_workspace_config(self, temp_workspace):
        """Test saving and loading workspace config."""
        test_config = {
            "paths": {
                "prompts": "my-prompts"
            },
            "variables": {
                "test_var": {
                    "type": "value",
                    "value": "test value"
                }
            }
        }

        # Save config
        result = config.save_workspace_config(temp_workspace, test_config)
        assert "✅" in result

        # Load and verify
        loaded = config.load_workspace_config(temp_workspace)
        assert loaded["paths"]["prompts"] == "my-prompts"
        assert "test_var" in loaded["variables"]
        assert loaded["variables"]["test_var"]["value"] == "test value"

    def test_validate_workspace_config_valid(self, temp_workspace):
        """Test validation of valid workspace config."""
        # Create prompts directory
        prompts_dir = Path(temp_workspace) / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        valid_config = {
            "paths": {
                "prompts": "prompts"
            },
            "variables": {}
        }

        errors = config.validate_workspace_config(temp_workspace, valid_config)
        assert len(errors) == 0

    def test_validate_workspace_config_missing_prompt_dir(self, temp_workspace):
        """Test validation catches missing prompt directory."""
        invalid_config = {
            "paths": {
                "prompts": "nonexistent"
            },
            "variables": {}
        }

        errors = config.validate_workspace_config(temp_workspace, invalid_config)
        assert any("not found" in err.lower() for err in errors)

    def test_validate_workspace_config_missing_variable_file(self, temp_workspace, sample_prompt_files):
        """Test validation catches missing variable files."""
        invalid_config = {
            "paths": {
                "prompts": "prompts"
            },
            "variables": {
                "test_var": {
                    "type": "file",
                    "path": "nonexistent.txt"
                }
            }
        }

        errors = config.validate_workspace_config(temp_workspace, invalid_config)
        assert any("not found" in err.lower() for err in errors)

    def test_validate_workspace_config_valid_variable_file(self, temp_workspace, sample_prompt_files, sample_variable_files):
        """Test validation passes for existing variable files."""
        valid_config = {
            "paths": {
                "prompts": "prompts"
            },
            "variables": {
                "code": {
                    "type": "file",
                    "path": "prompt-data/code.py"
                }
            }
        }

        errors = config.validate_workspace_config(temp_workspace, valid_config)
        assert len(errors) == 0
