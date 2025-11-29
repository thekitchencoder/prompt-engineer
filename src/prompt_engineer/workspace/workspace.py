"""
Main workspace management system.

Manages workspace configuration, file discovery, and provides high-level operations.
"""

from typing import Optional, List, Dict
from pathlib import Path
from .config import WorkspaceConfig, WorkspacePresets
from .discovery import WorkspaceDiscovery, PromptSet, ProjectType
from ..templates.parser import TemplateParser
from ..templates.resolver import TemplateResolver
from ..templates.models import Template, Variable, Prompt, PromptRole, VariableType
import yaml


class WorkspaceError(Exception):
    """Base exception for workspace errors."""
    pass


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when workspace configuration is not found."""
    pass


class Workspace:
    """
    Main workspace management class.

    Provides high-level operations for working with prompt engineering workspaces.
    """

    def __init__(self, root_path: Path, config: Optional[WorkspaceConfig] = None):
        """
        Initialize workspace.

        Args:
            root_path: Root directory of the workspace
            config: Workspace configuration (loaded from file if not provided)
        """
        self.root_path = Path(root_path).resolve()
        self._config = config
        self._prompt_sets: Optional[List[PromptSet]] = None
        self._warnings: List[str] = []

        # Initialize components
        if self._config:
            self._init_components()

    @property
    def config(self) -> WorkspaceConfig:
        """Get workspace configuration (loads from file if needed)."""
        if self._config is None:
            self._config = self._load_config()
            self._init_components()
        return self._config

    def _init_components(self):
        """Initialize workspace components based on configuration."""
        if not self._config:
            return

        # Create discovery system
        self.discovery = WorkspaceDiscovery(
            workspace_root=self.root_path,
            prompt_extension=self._config.layout.prompt_extension,
            vars_extension=self._config.layout.vars_extension,
            naming_pattern=self._config.template.naming.pattern
        )

        # Create parser with configured delimiters
        self.parser = TemplateParser(
            delimiter=self._config.template.variable_delimiters
        )

        # Create resolver with workspace base path
        self.resolver = TemplateResolver(
            delimiter=self._config.template.variable_delimiters,
            base_path=self.root_path
        )

    def _load_config(self) -> WorkspaceConfig:
        """
        Load workspace configuration from file.

        Returns:
            WorkspaceConfig instance

        Raises:
            WorkspaceNotFoundError: If config file doesn't exist
        """
        config_path = self.root_path / ".prompt-engineer" / "workspace.yaml"

        if not config_path.exists():
            raise WorkspaceNotFoundError(
                f"Workspace configuration not found at {config_path}. "
                f"Use Workspace.create() to initialize a new workspace."
            )

        return WorkspaceConfig.from_yaml_file(config_path)

    @classmethod
    def create(
        cls,
        root_path: Path,
        name: str,
        preset: Optional[str] = None,
        auto_detect: bool = True
    ) -> "Workspace":
        """
        Create a new workspace.

        Args:
            root_path: Root directory for the workspace
            name: Workspace name
            preset: Preset name ("springboot", "python", "nodejs", "custom")
            auto_detect: Auto-detect project type if preset not specified

        Returns:
            Workspace instance
        """
        root_path = Path(root_path).resolve()

        # Get configuration (from preset or auto-detection)
        if preset:
            config = WorkspacePresets.get_preset(preset)
            if not config:
                raise ValueError(f"Unknown preset: {preset}")
            config.name = name
        elif auto_detect:
            # Auto-detect project type and create appropriate config
            discovery = WorkspaceDiscovery(root_path)
            project_type = discovery.detect_project_type()
            layout = discovery.suggest_layout()

            # Map project type to preset
            preset_map = {
                ProjectType.MAVEN: "springboot",
                ProjectType.GRADLE: "springboot",
                ProjectType.PYTHON: "python",
                ProjectType.NODEJS: "nodejs",
                ProjectType.UNKNOWN: "custom"
            }

            preset_name = preset_map.get(project_type, "custom")
            config = WorkspacePresets.get_preset(preset_name)
            config.name = name
        else:
            config = WorkspacePresets.custom()
            config.name = name

        # Save configuration
        config_path = root_path / ".prompt-engineer" / "workspace.yaml"
        config.to_yaml_file(config_path)

        # Create workspace instance
        return cls(root_path, config)

    @classmethod
    def load(cls, root_path: Path) -> "Workspace":
        """
        Load an existing workspace.

        Args:
            root_path: Root directory of the workspace

        Returns:
            Workspace instance

        Raises:
            WorkspaceNotFoundError: If workspace config doesn't exist
        """
        return cls(root_path)

    def discover_prompts(self, force_refresh: bool = False) -> List[PromptSet]:
        """
        Discover all prompts and variables in the workspace.

        Args:
            force_refresh: Force re-discovery even if already cached

        Returns:
            List of PromptSet objects
        """
        if self._prompt_sets is not None and not force_refresh:
            return self._prompt_sets

        prompt_dir = self.config.layout.get_prompt_dir(self.root_path)
        vars_dir = self.config.layout.get_vars_dir(self.root_path)

        self._prompt_sets, self._warnings = self.discovery.discover(
            prompt_dir=prompt_dir,
            vars_dir=vars_dir
        )

        return self._prompt_sets

    def get_prompt_set(self, name: str) -> Optional[PromptSet]:
        """
        Get a specific prompt set by name.

        Args:
            name: Name of the prompt set

        Returns:
            PromptSet or None if not found
        """
        prompt_sets = self.discover_prompts()

        for ps in prompt_sets:
            if ps.name == name:
                return ps

        return None

    def load_template(self, name: str) -> Optional[Template]:
        """
        Load a complete template by name.

        Args:
            name: Template name

        Returns:
            Template instance or None if not found
        """
        prompt_set = self.get_prompt_set(name)
        if not prompt_set or not prompt_set.var_file:
            return None

        # Load variable configuration
        var_file_path = prompt_set.var_file.path

        try:
            with open(var_file_path, 'r') as f:
                var_config = yaml.safe_load(f)
        except Exception as e:
            raise WorkspaceError(f"Error loading variable file {var_file_path}: {e}")

        # Handle empty or invalid YAML (None or not a dict)
        if not isinstance(var_config, dict):
            var_config = {}

        # Create template
        template = Template(
            name=name,
            description=var_config.get("description")
        )

        # Add prompts
        for role, prompt_file in prompt_set.prompts.items():
            try:
                # Map "prompt" role (single-file prompts) to USER role
                if role == "prompt":
                    prompt_role = PromptRole.USER
                else:
                    prompt_role = PromptRole(role)

                prompt = Prompt(
                    role=prompt_role,
                    file_path=str(prompt_file.path.relative_to(self.root_path)),
                    name=name
                )
                template.add_prompt(prompt)
            except ValueError:
                # Unknown role, skip
                pass

        # Add variables from config
        variables_config = var_config.get("variables", {})
        for var_name, var_def in variables_config.items():
            var_type = VariableType(var_def.get("type", "value"))

            if var_type == VariableType.FILE:
                content = var_def.get("path", "")
            else:
                content = var_def.get("value", "")

            variable = Variable(
                name=var_name,
                type=var_type,
                content=content,
                description=var_def.get("description")
            )
            template.add_variable(variable)

        return template

    def get_warnings(self) -> List[str]:
        """
        Get warnings from last discovery operation.

        Returns:
            List of warning messages
        """
        return self._warnings.copy()

    def get_prompt_dir(self) -> Path:
        """Get absolute path to prompts directory."""
        return self.config.layout.get_prompt_dir(self.root_path)

    def get_vars_dir(self) -> Path:
        """Get absolute path to variables directory."""
        return self.config.layout.get_vars_dir(self.root_path)

    def get_chains_dir(self) -> Optional[Path]:
        """Get absolute path to chains directory (if configured)."""
        return self.config.layout.get_chains_dir(self.root_path)

    def save_config(self):
        """Save current configuration to file."""
        config_path = self.root_path / ".prompt-engineer" / "workspace.yaml"
        self.config.to_yaml_file(config_path)

    def __repr__(self) -> str:
        """String representation of workspace."""
        return f"Workspace(name='{self.config.name}', root='{self.root_path}')"


class WorkspaceManager:
    """
    Manages multiple workspaces.

    Provides workspace discovery and management operations.
    """

    def __init__(self):
        """Initialize workspace manager."""
        self.current_workspace: Optional[Workspace] = None
        self.recent_workspaces: List[Path] = []

    def open_workspace(self, root_path: Path) -> Workspace:
        """
        Open an existing workspace.

        Args:
            root_path: Root directory of the workspace

        Returns:
            Workspace instance
        """
        workspace = Workspace.load(root_path)
        self.current_workspace = workspace

        # Add to recent workspaces
        if root_path not in self.recent_workspaces:
            self.recent_workspaces.insert(0, root_path)
            # Keep only last 10
            self.recent_workspaces = self.recent_workspaces[:10]

        return workspace

    def create_workspace(
        self,
        root_path: Path,
        name: str,
        preset: Optional[str] = None
    ) -> Workspace:
        """
        Create a new workspace.

        Args:
            root_path: Root directory for the workspace
            name: Workspace name
            preset: Preset name (optional)

        Returns:
            Workspace instance
        """
        workspace = Workspace.create(root_path, name, preset)
        self.current_workspace = workspace

        # Add to recent workspaces
        if root_path not in self.recent_workspaces:
            self.recent_workspaces.insert(0, root_path)
            self.recent_workspaces = self.recent_workspaces[:10]

        return workspace

    def close_workspace(self):
        """Close the current workspace."""
        self.current_workspace = None

    def get_current_workspace(self) -> Optional[Workspace]:
        """Get the currently active workspace."""
        return self.current_workspace

    def get_recent_workspaces(self) -> List[Path]:
        """Get list of recently opened workspaces."""
        return self.recent_workspaces.copy()
