"""
Workspace configuration schema and models.

Defines the structure of workspace.yaml files using Pydantic for validation.
"""

from typing import Optional, Dict, List, Any, Literal
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
import yaml


class VariableConfig(BaseModel):
    """Configuration for a single variable."""

    type: Literal["file", "value"] = Field(
        description="Variable type: 'file' to load from file, 'value' for direct value"
    )
    path: Optional[str] = Field(
        default=None,
        description="Path to file (relative to workspace root) when type='file'"
    )
    value: Optional[str] = Field(
        default=None,
        description="Direct value when type='value'"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the variable"
    )

    @field_validator("path")
    @classmethod
    def validate_path_for_file_type(cls, v, info):
        """Ensure path is provided when type is 'file'."""
        if info.data.get("type") == "file" and not v:
            raise ValueError("'path' is required when type='file'")
        return v

    @field_validator("value")
    @classmethod
    def validate_value_for_value_type(cls, v, info):
        """Ensure value is provided when type is 'value'."""
        if info.data.get("type") == "value" and not v:
            raise ValueError("'value' is required when type='value'")
        return v


class VariableDelimiters(BaseModel):
    """Configuration for variable delimiters in templates."""

    start: str = Field(default="{", description="Start delimiter (e.g., '{', '$', '<')")
    end: str = Field(default="}", description="End delimiter (e.g., '}', '$', '>')")

    def __str__(self) -> str:
        return f"{self.start}variable{self.end}"


class NamingConfig(BaseModel):
    """File naming conventions for prompts and variables."""

    pattern: str = Field(
        default="{role}-{name}.st",
        description="Pattern for prompt files (e.g., 'system-evaluator.st')"
    )
    roles: List[str] = Field(
        default=["system", "user"],
        description="Recognized prompt roles"
    )
    var_pattern: str = Field(
        default="{name}.yaml",
        description="Pattern for variable files (e.g., 'evaluator.yaml')"
    )


class MatchingConfig(BaseModel):
    """Auto-matching behavior configuration."""

    auto_match: bool = Field(
        default=True,
        description="Auto-match prompt files to variable files by name"
    )
    allow_override: bool = Field(
        default=True,
        description="Allow manual override in variable files"
    )
    warn_orphans: bool = Field(
        default=True,
        description="Warn about prompts without matching variable files"
    )


class TemplateConfig(BaseModel):
    """Template syntax configuration."""

    variable_delimiters: VariableDelimiters = Field(
        default_factory=VariableDelimiters,
        description="Variable delimiter configuration"
    )
    naming: NamingConfig = Field(
        default_factory=NamingConfig,
        description="File naming conventions"
    )
    matching: MatchingConfig = Field(
        default_factory=MatchingConfig,
        description="Auto-matching behavior"
    )


class LayoutConfig(BaseModel):
    """Project layout configuration."""

    prompt_dir: str = Field(
        default="prompts",
        description="Directory containing prompt files"
    )
    vars_dir: str = Field(
        default="prompts/vars",
        description="Directory containing variable configuration files"
    )
    chains_dir: Optional[str] = Field(
        default=None,
        description="Directory containing chain configuration files (optional)"
    )
    prompt_extension: str = Field(
        default=".st",
        description="File extension for prompt files"
    )
    vars_extension: str = Field(
        default=".yaml",
        description="File extension for variable files"
    )

    def get_prompt_dir(self, workspace_root: Path) -> Path:
        """Get absolute path to prompts directory."""
        return workspace_root / self.prompt_dir

    def get_vars_dir(self, workspace_root: Path) -> Path:
        """Get absolute path to variables directory."""
        return workspace_root / self.vars_dir

    def get_chains_dir(self, workspace_root: Path) -> Optional[Path]:
        """Get absolute path to chains directory (if configured)."""
        if self.chains_dir:
            return workspace_root / self.chains_dir
        return None


class GitConfig(BaseModel):
    """Git integration configuration."""

    show_status: bool = Field(default=True, description="Show git status in UI")
    show_branch: bool = Field(default=True, description="Show current branch")
    show_uncommitted: bool = Field(default=True, description="Show uncommitted changes count")


class DefaultsConfig(BaseModel):
    """Default model settings for workspace."""

    provider: str = Field(default="openai", description="Default provider name")
    model: str = Field(default="gpt-4o", description="Default model ID")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Default temperature")
    max_tokens: int = Field(default=2000, ge=1, description="Default max tokens")


class WorkspaceSettings(BaseModel):
    """Workspace-specific settings."""

    auto_reload: bool = Field(
        default=True,
        description="Watch for external file changes and auto-reload"
    )
    auto_extract_vars: bool = Field(
        default=True,
        description="Auto-detect variables in prompts"
    )
    auto_save: bool = Field(
        default=False,
        description="Auto-save on change"
    )


class WorkspaceConfig(BaseModel):
    """
    Complete workspace configuration.

    Represents the structure of a .prompt-engineer/workspace.yaml file.
    """

    name: str = Field(..., description="Workspace name")
    version: str = Field(default="1.0", description="Config version")
    layout: LayoutConfig = Field(
        default_factory=LayoutConfig,
        description="Project layout configuration"
    )
    template: TemplateConfig = Field(
        default_factory=TemplateConfig,
        description="Template syntax configuration"
    )
    git: GitConfig = Field(
        default_factory=GitConfig,
        description="Git integration configuration"
    )
    defaults: DefaultsConfig = Field(
        default_factory=DefaultsConfig,
        description="Default model settings"
    )
    settings: WorkspaceSettings = Field(
        default_factory=WorkspaceSettings,
        description="Workspace settings"
    )
    variables: Dict[str, VariableConfig] = Field(
        default_factory=dict,
        description="Global variables for all prompts"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    @classmethod
    def from_yaml_file(cls, file_path: Path) -> "WorkspaceConfig":
        """
        Load workspace configuration from YAML file.

        Args:
            file_path: Path to workspace.yaml file

        Returns:
            WorkspaceConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Workspace config not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            return cls(**data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in workspace config: {e}")
        except Exception as e:
            raise ValueError(f"Error loading workspace config: {e}")

    def to_yaml_file(self, file_path: Path):
        """
        Save workspace configuration to YAML file.

        Args:
            file_path: Path where to save workspace.yaml
        """
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary and write YAML
        data = self.model_dump(exclude_none=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )

    def get_variable_value(self, var_name: str, workspace_root: Path) -> Optional[str]:
        """
        Get the resolved value of a variable.

        Args:
            var_name: Name of the variable
            workspace_root: Path to workspace root directory

        Returns:
            Variable value (file contents or direct value), or None if not found
        """
        if var_name not in self.variables:
            return None

        var_config = self.variables[var_name]

        if var_config.type == "file":
            # Load from file
            file_path = workspace_root / var_config.path
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return None
        else:
            # Direct value
            return var_config.value

    def get_all_variables(self, workspace_root: Path) -> Dict[str, str]:
        """
        Get all variables resolved to their values.

        Args:
            workspace_root: Path to workspace root directory

        Returns:
            Dictionary of variable names to resolved values
        """
        result = {}
        for var_name in self.variables:
            value = self.get_variable_value(var_name, workspace_root)
            if value is not None:
                result[var_name] = value
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(exclude_none=True)


class WorkspacePresets:
    """Preset workspace configurations for common project types."""

    @staticmethod
    def springboot() -> WorkspaceConfig:
        """SpringBoot/Maven project preset."""
        return WorkspaceConfig(
            name="SpringBoot Project",
            version="1.0",
            layout=LayoutConfig(
                prompt_dir="src/main/resources/prompts",
                vars_dir="src/test/resources/prompts/vars",
                chains_dir="src/test/resources/prompts/chains",
                prompt_extension=".st",
                vars_extension=".yaml"
            ),
            template=TemplateConfig(
                variable_delimiters=VariableDelimiters(start="{", end="}"),
                naming=NamingConfig(
                    pattern="{role}-{name}.st",
                    roles=["system", "user"],
                    var_pattern="{name}.yaml"
                )
            )
        )

    @staticmethod
    def python() -> WorkspaceConfig:
        """Python project preset."""
        return WorkspaceConfig(
            name="Python Project",
            version="1.0",
            layout=LayoutConfig(
                prompt_dir="app/prompts",
                vars_dir="app/prompts/vars",
                chains_dir="app/prompts/chains",
                prompt_extension=".txt",
                vars_extension=".yaml"
            ),
            template=TemplateConfig(
                variable_delimiters=VariableDelimiters(start="{", end="}"),
                naming=NamingConfig(
                    pattern="{role}-{name}.txt",
                    roles=["system", "user"],
                    var_pattern="{name}.yaml"
                )
            )
        )

    @staticmethod
    def nodejs() -> WorkspaceConfig:
        """Node.js project preset."""
        return WorkspaceConfig(
            name="Node.js Project",
            version="1.0",
            layout=LayoutConfig(
                prompt_dir="src/prompts",
                vars_dir="src/prompts/vars",
                chains_dir="src/prompts/chains",
                prompt_extension=".txt",
                vars_extension=".yaml"
            ),
            template=TemplateConfig(
                variable_delimiters=VariableDelimiters(start="{", end="}"),
                naming=NamingConfig(
                    pattern="{role}-{name}.txt",
                    roles=["system", "user"],
                    var_pattern="{name}.yaml"
                )
            )
        )

    @staticmethod
    def custom() -> WorkspaceConfig:
        """Custom project preset with default settings."""
        return WorkspaceConfig(
            name="Custom Project",
            version="1.0",
            layout=LayoutConfig(
                prompt_dir="prompts",
                vars_dir="prompts/vars",
                prompt_extension=".txt",
                vars_extension=".yaml"
            )
        )

    @classmethod
    def get_preset(cls, preset_name: str) -> Optional[WorkspaceConfig]:
        """
        Get workspace preset by name.

        Args:
            preset_name: Name of preset ("springboot", "python", "nodejs", "custom")

        Returns:
            WorkspaceConfig instance or None if preset not found
        """
        presets = {
            "springboot": cls.springboot,
            "python": cls.python,
            "nodejs": cls.nodejs,
            "custom": cls.custom
        }

        preset_func = presets.get(preset_name.lower())
        return preset_func() if preset_func else None

    @classmethod
    def list_presets(cls) -> List[str]:
        """Get list of available preset names."""
        return ["springboot", "python", "nodejs", "custom"]
