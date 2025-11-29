"""
Data models for templates, variables, and prompts.

Defines the core data structures used throughout the template system.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
from enum import Enum
from datetime import datetime


class VariableType(str, Enum):
    """Type of variable value source."""
    FILE = "file"
    VALUE = "value"


class PromptRole(str, Enum):
    """Role of a prompt in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    CONTEXT = "context"


class Variable(BaseModel):
    """
    A variable that can be interpolated into a prompt template.

    Variables can either reference a file (whose contents are loaded)
    or contain a direct value.
    """

    name: str = Field(..., description="Variable name (used in template)")
    type: VariableType = Field(..., description="Type of variable (file or value)")
    content: str = Field(..., description="File path or direct value")
    description: Optional[str] = Field(None, description="Description of variable purpose")

    def resolve(self, base_path: Optional[Path] = None) -> str:
        """
        Resolve the variable to its actual value.

        For FILE type: reads and returns file contents
        For VALUE type: returns the content directly

        Args:
            base_path: Base directory for resolving relative file paths

        Returns:
            Resolved variable value

        Raises:
            FileNotFoundError: If file type variable points to non-existent file
        """
        if self.type == VariableType.VALUE:
            return self.content

        # FILE type - load from file
        file_path = Path(self.content)

        # Make absolute if base_path provided and path is relative
        if base_path and not file_path.is_absolute():
            file_path = base_path / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"Variable '{self.name}' references non-existent file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Error reading file for variable '{self.name}': {e}")

    @classmethod
    def from_file(cls, name: str, file_path: str, description: Optional[str] = None) -> "Variable":
        """Create a file-type variable."""
        return cls(
            name=name,
            type=VariableType.FILE,
            content=file_path,
            description=description
        )

    @classmethod
    def from_value(cls, name: str, value: str, description: Optional[str] = None) -> "Variable":
        """Create a value-type variable."""
        return cls(
            name=name,
            type=VariableType.VALUE,
            content=value,
            description=description
        )


class Prompt(BaseModel):
    """
    A prompt with a specific role (system, user, etc.).

    Prompts are loaded from files and contain template text with variable placeholders.
    """

    role: PromptRole = Field(..., description="Role of this prompt")
    file_path: str = Field(..., description="Path to prompt file")
    content: Optional[str] = Field(None, description="Loaded prompt content (cached)")
    name: Optional[str] = Field(None, description="Name of the prompt")

    def load_content(self, base_path: Optional[Path] = None) -> str:
        """
        Load prompt content from file.

        Args:
            base_path: Base directory for resolving relative paths

        Returns:
            Prompt template content

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        file_path = Path(self.file_path)

        # Make absolute if base_path provided and path is relative
        if base_path and not file_path.is_absolute():
            file_path = base_path / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
                return self.content
        except Exception as e:
            raise RuntimeError(f"Error reading prompt file '{file_path}': {e}")

    def get_content(self, base_path: Optional[Path] = None) -> str:
        """
        Get prompt content (loads if not cached).

        Args:
            base_path: Base directory for resolving relative paths

        Returns:
            Prompt content
        """
        if self.content is None:
            return self.load_content(base_path)
        return self.content

    @classmethod
    def from_file(cls, role: PromptRole, file_path: str, name: Optional[str] = None) -> "Prompt":
        """Create a prompt from a file."""
        return cls(role=role, file_path=file_path, name=name)


class Template(BaseModel):
    """
    A complete prompt template with variables and prompts.

    Templates combine one or more prompts (system, user, etc.) with
    variable definitions for interpolation.
    """

    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    prompts: Dict[PromptRole, Prompt] = Field(
        default_factory=dict,
        description="Prompts by role (system, user, etc.)"
    )
    variables: Dict[str, Variable] = Field(
        default_factory=dict,
        description="Variables available for interpolation"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    created: Optional[datetime] = Field(None, description="Creation timestamp")
    last_modified: Optional[datetime] = Field(None, description="Last modification timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def add_prompt(self, prompt: Prompt) -> "Template":
        """Add a prompt to the template."""
        self.prompts[prompt.role] = prompt
        return self

    def add_variable(self, variable: Variable) -> "Template":
        """Add a variable to the template."""
        self.variables[variable.name] = variable
        return self

    def get_prompt(self, role: PromptRole) -> Optional[Prompt]:
        """Get prompt by role."""
        return self.prompts.get(role)

    def get_variable(self, name: str) -> Optional[Variable]:
        """Get variable by name."""
        return self.variables.get(name)

    def has_prompt(self, role: PromptRole) -> bool:
        """Check if template has a prompt for the given role."""
        return role in self.prompts

    def has_variable(self, name: str) -> bool:
        """Check if template has a variable with the given name."""
        return name in self.variables

    def get_all_variables_dict(self, base_path: Optional[Path] = None) -> Dict[str, str]:
        """
        Resolve all variables to their values.

        Args:
            base_path: Base directory for resolving file paths

        Returns:
            Dictionary mapping variable names to resolved values
        """
        return {
            name: var.resolve(base_path)
            for name, var in self.variables.items()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary format."""
        return {
            "name": self.name,
            "description": self.description,
            "prompts": {
                role.value: {
                    "file_path": prompt.file_path,
                    "name": prompt.name
                }
                for role, prompt in self.prompts.items()
            },
            "variables": {
                name: {
                    "type": var.type.value,
                    "content": var.content,
                    "description": var.description
                }
                for name, var in self.variables.items()
            },
            "tags": self.tags,
            "metadata": self.metadata
        }


class TemplateConfig(BaseModel):
    """
    Configuration for loading templates from YAML files.

    Represents the structure of a .yaml variable configuration file.
    """

    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    prompts: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of role to file path (e.g., {'system': 'system-evaluator.st'})"
    )
    variables: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Variable definitions"
    )
    model: Optional[Dict[str, Any]] = Field(None, description="Model settings override")
    tags: List[str] = Field(default_factory=list, description="Tags")
    created: Optional[str] = Field(None, description="Creation date")
    last_modified: Optional[str] = Field(None, description="Last modified date")

    def to_template(self) -> Template:
        """
        Convert config to Template instance.

        Returns:
            Template instance
        """
        template = Template(
            name=self.name,
            description=self.description,
            tags=self.tags
        )

        # Add prompts
        for role_str, file_path in self.prompts.items():
            try:
                role = PromptRole(role_str)
                prompt = Prompt.from_file(role, file_path, name=f"{self.name}-{role_str}")
                template.add_prompt(prompt)
            except ValueError:
                # Unknown role, skip
                pass

        # Add variables
        for var_name, var_config in self.variables.items():
            var_type = VariableType(var_config.get("type", "value"))
            content = var_config.get("path" if var_type == VariableType.FILE else "value", "")
            description = var_config.get("description")

            variable = Variable(
                name=var_name,
                type=var_type,
                content=content,
                description=description
            )
            template.add_variable(variable)

        return template
