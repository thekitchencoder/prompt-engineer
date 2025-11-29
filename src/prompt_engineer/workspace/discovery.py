"""
Project type detection and file discovery for workspaces.

Auto-detects project structure and discovers prompt/variable files.
"""

from typing import Optional, List, Dict, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import re


class ProjectType(str, Enum):
    """Detected project type."""
    MAVEN = "maven"
    GRADLE = "gradle"
    PYTHON = "python"
    NODEJS = "nodejs"
    UNKNOWN = "unknown"


@dataclass
class PromptFile:
    """Discovered prompt file."""
    path: Path
    role: Optional[str]  # e.g., "system", "user"
    name: Optional[str]  # e.g., "evaluator"
    full_name: str       # e.g., "system-evaluator"


@dataclass
class VarFile:
    """Discovered variable configuration file."""
    path: Path
    name: str  # e.g., "evaluator"


@dataclass
class PromptSet:
    """A set of related prompts matched to a variable file."""
    name: str
    var_file: Optional[VarFile]
    prompts: Dict[str, PromptFile]  # role -> PromptFile
    is_orphaned: bool = False


class ProjectDetector:
    """Detects project type from directory structure."""

    @staticmethod
    def detect(workspace_root: Path) -> ProjectType:
        """
        Auto-detect project type from workspace directory.

        Args:
            workspace_root: Root directory of the project

        Returns:
            Detected ProjectType
        """
        if not workspace_root.exists():
            return ProjectType.UNKNOWN

        # Maven project
        if (workspace_root / "pom.xml").exists():
            return ProjectType.MAVEN

        # Gradle project
        if (workspace_root / "build.gradle").exists() or (workspace_root / "build.gradle.kts").exists():
            return ProjectType.GRADLE

        # Node.js project
        if (workspace_root / "package.json").exists():
            return ProjectType.NODEJS

        # Python project
        if (
            (workspace_root / "requirements.txt").exists()
            or (workspace_root / "pyproject.toml").exists()
            or (workspace_root / "setup.py").exists()
        ):
            return ProjectType.PYTHON

        return ProjectType.UNKNOWN

    @staticmethod
    def suggest_layout(project_type: ProjectType) -> Dict[str, str]:
        """
        Suggest workspace layout based on project type.

        Args:
            project_type: Detected project type

        Returns:
            Dictionary with suggested paths
        """
        layouts = {
            ProjectType.MAVEN: {
                "prompt_dir": "src/main/resources/prompts",
                "vars_dir": "src/test/resources/prompts/vars",
                "chains_dir": "src/test/resources/prompts/chains",
                "prompt_extension": ".st",
                "vars_extension": ".yaml"
            },
            ProjectType.GRADLE: {
                "prompt_dir": "src/main/resources/prompts",
                "vars_dir": "src/test/resources/prompts/vars",
                "chains_dir": "src/test/resources/prompts/chains",
                "prompt_extension": ".st",
                "vars_extension": ".yaml"
            },
            ProjectType.PYTHON: {
                "prompt_dir": "app/prompts",
                "vars_dir": "app/prompts/vars",
                "chains_dir": "app/prompts/chains",
                "prompt_extension": ".txt",
                "vars_extension": ".yaml"
            },
            ProjectType.NODEJS: {
                "prompt_dir": "src/prompts",
                "vars_dir": "src/prompts/vars",
                "chains_dir": "src/prompts/chains",
                "prompt_extension": ".txt",
                "vars_extension": ".yaml"
            },
            ProjectType.UNKNOWN: {
                "prompt_dir": "prompts",
                "vars_dir": "prompts/vars",
                "prompt_extension": ".txt",
                "vars_extension": ".yaml"
            }
        }

        return layouts.get(project_type, layouts[ProjectType.UNKNOWN])


class FileScanner:
    """Scans directories for prompt and variable files."""

    def __init__(
        self,
        prompt_extension: str = ".st",
        vars_extension: str = ".yaml",
        naming_pattern: str = "{role}-{name}"
    ):
        """
        Initialize file scanner.

        Args:
            prompt_extension: Extension for prompt files (e.g., ".st", ".txt")
            vars_extension: Extension for variable files (e.g., ".yaml")
            naming_pattern: Naming pattern for prompts (e.g., "{role}-{name}")
        """
        self.prompt_extension = prompt_extension
        self.vars_extension = vars_extension
        self.naming_pattern = naming_pattern

    def scan_prompts(self, prompt_dir: Path) -> List[PromptFile]:
        """
        Scan directory for prompt files.

        Args:
            prompt_dir: Directory to scan

        Returns:
            List of discovered PromptFile objects
        """
        if not prompt_dir.exists():
            return []

        prompt_files = []

        for file_path in prompt_dir.glob(f"**/*{self.prompt_extension}"):
            if file_path.is_file():
                role, name = self._parse_prompt_filename(file_path.stem)
                prompt_files.append(PromptFile(
                    path=file_path,
                    role=role,
                    name=name,
                    full_name=file_path.stem
                ))

        return prompt_files

    def scan_vars(self, vars_dir: Path) -> List[VarFile]:
        """
        Scan directory for variable configuration files.

        Args:
            vars_dir: Directory to scan

        Returns:
            List of discovered VarFile objects
        """
        if not vars_dir.exists():
            return []

        var_files = []

        # Support multiple extensions: .yaml, .yml, and legacy .vars
        extensions = [self.vars_extension, '.vars', '.yml']

        for ext in extensions:
            for file_path in vars_dir.glob(f"**/*{ext}"):
                if file_path.is_file():
                    # Extract name from filename (without extension)
                    name = file_path.stem
                    # Avoid duplicates if same file has multiple extensions
                    if not any(vf.name == name for vf in var_files):
                        var_files.append(VarFile(
                            path=file_path,
                            name=name
                        ))

        return var_files

    def _parse_prompt_filename(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse prompt filename to extract role and name.

        Args:
            filename: Filename without extension (e.g., "system-evaluator" or "evaluator")

        Returns:
            Tuple of (role, name)

        Example:
            >>> scanner._parse_prompt_filename("system-evaluator")
            ("system", "evaluator")
            >>> scanner._parse_prompt_filename("evaluator")
            (None, "evaluator")  # Single-file prompt without role
        """
        # Try to match pattern: {role}-{name}
        # Common roles: system, user, assistant, context
        parts = filename.split('-', 1)

        if len(parts) == 2:
            role, name = parts
            # Validate role (common role names)
            if role in ['system', 'user', 'assistant', 'context']:
                return (role, name)

        # No role prefix - treat as single-file prompt with implicit "user" role
        # This allows files like "data_analysis.txt" to be discovered
        return (None, filename)


class PromptMatcher:
    """Matches prompt files to variable files based on naming conventions."""

    def __init__(self, warn_orphans: bool = True):
        """
        Initialize prompt matcher.

        Args:
            warn_orphans: Whether to warn about orphaned prompts
        """
        self.warn_orphans = warn_orphans

    def match(
        self,
        prompt_files: List[PromptFile],
        var_files: List[VarFile]
    ) -> List[PromptSet]:
        """
        Match prompt files to variable files.

        Groups prompts by name and matches them to corresponding variable files.

        Args:
            prompt_files: List of discovered prompt files
            var_files: List of discovered variable files

        Returns:
            List of PromptSet objects (matched and orphaned)
        """
        # Group prompts by name
        prompts_by_name: Dict[str, Dict[str, PromptFile]] = {}

        for prompt in prompt_files:
            if prompt.name:
                if prompt.name not in prompts_by_name:
                    prompts_by_name[prompt.name] = {}
                # Use role if available, otherwise use "prompt" for single-file prompts
                role_key = prompt.role if prompt.role else "prompt"
                prompts_by_name[prompt.name][role_key] = prompt

        # Create var_files lookup
        vars_by_name = {vf.name: vf for vf in var_files}

        # Match prompts to vars
        prompt_sets = []

        # Process matched sets
        for name, prompts in prompts_by_name.items():
            var_file = vars_by_name.get(name)
            is_orphaned = var_file is None

            prompt_set = PromptSet(
                name=name,
                var_file=var_file,
                prompts=prompts,
                is_orphaned=is_orphaned
            )
            prompt_sets.append(prompt_set)

        # Add orphaned prompts (files that don't match naming pattern)
        orphaned_prompts = [p for p in prompt_files if p.name is None]
        for prompt in orphaned_prompts:
            prompt_set = PromptSet(
                name=prompt.full_name,
                var_file=None,
                prompts={"unknown": prompt},
                is_orphaned=True
            )
            prompt_sets.append(prompt_set)

        # Sort: non-orphaned first, then by name
        prompt_sets.sort(key=lambda ps: (ps.is_orphaned, ps.name))

        return prompt_sets

    def get_orphaned_prompts(self, prompt_sets: List[PromptSet]) -> List[PromptSet]:
        """
        Get list of orphaned prompt sets.

        Args:
            prompt_sets: List of all prompt sets

        Returns:
            List of orphaned PromptSet objects
        """
        return [ps for ps in prompt_sets if ps.is_orphaned]

    def get_matched_prompts(self, prompt_sets: List[PromptSet]) -> List[PromptSet]:
        """
        Get list of matched prompt sets.

        Args:
            prompt_sets: List of all prompt sets

        Returns:
            List of matched PromptSet objects
        """
        return [ps for ps in prompt_sets if not ps.is_orphaned]


class WorkspaceDiscovery:
    """
    Complete workspace discovery system.

    Combines project detection, file scanning, and prompt matching.
    """

    def __init__(
        self,
        workspace_root: Path,
        prompt_extension: str = ".st",
        vars_extension: str = ".yaml",
        naming_pattern: str = "{role}-{name}"
    ):
        """
        Initialize workspace discovery.

        Args:
            workspace_root: Root directory of the workspace
            prompt_extension: Extension for prompt files
            vars_extension: Extension for variable files
            naming_pattern: Naming pattern for prompts
        """
        self.workspace_root = workspace_root
        self.scanner = FileScanner(prompt_extension, vars_extension, naming_pattern)
        self.matcher = PromptMatcher(warn_orphans=True)

    def discover(
        self,
        prompt_dir: Path,
        vars_dir: Path
    ) -> Tuple[List[PromptSet], List[str]]:
        """
        Discover and match all prompts and variables.

        Args:
            prompt_dir: Directory containing prompts
            vars_dir: Directory containing variable configs

        Returns:
            Tuple of (prompt_sets, warnings)
        """
        warnings = []

        # Scan for files
        prompt_files = self.scanner.scan_prompts(prompt_dir)
        var_files = self.scanner.scan_vars(vars_dir)

        # Match prompts to vars
        prompt_sets = self.matcher.match(prompt_files, var_files)

        # Generate warnings for orphaned prompts
        orphaned = self.matcher.get_orphaned_prompts(prompt_sets)
        if orphaned:
            warnings.append(
                f"Found {len(orphaned)} orphaned prompt(s) without matching variable files"
            )
            for ps in orphaned:
                warnings.append(f"  - {ps.name}")

        return (prompt_sets, warnings)

    def detect_project_type(self) -> ProjectType:
        """
        Detect project type from workspace.

        Returns:
            Detected ProjectType
        """
        return ProjectDetector.detect(self.workspace_root)

    def suggest_layout(self) -> Dict[str, str]:
        """
        Suggest workspace layout based on detected project type.

        Returns:
            Dictionary with suggested paths
        """
        project_type = self.detect_project_type()
        return ProjectDetector.suggest_layout(project_type)
