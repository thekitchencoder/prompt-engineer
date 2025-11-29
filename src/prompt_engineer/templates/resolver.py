"""
Template resolver for variable interpolation.

Resolves variables in templates and produces final prompts ready for LLM consumption.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
from .models import Template, Variable, Prompt, PromptRole
from .parser import TemplateParser, DelimiterConfig


class ResolutionError(Exception):
    """Raised when template resolution fails."""
    pass


class MissingVariableError(ResolutionError):
    """Raised when a required variable is missing."""
    pass


class TemplateResolver:
    """
    Resolves variables in templates to produce final prompts.

    Handles variable interpolation with support for file-based and value-based variables.
    """

    def __init__(self, delimiter: Optional[DelimiterConfig] = None, base_path: Optional[Path] = None):
        """
        Initialize template resolver.

        Args:
            delimiter: Delimiter configuration for variable parsing
            base_path: Base directory for resolving relative file paths
        """
        self.parser = TemplateParser(delimiter)
        self.base_path = base_path or Path.cwd()

    def resolve_template(
        self,
        template_text: str,
        variables: Dict[str, str],
        strict: bool = True
    ) -> str:
        """
        Resolve variables in a template text.

        Args:
            template_text: Template text with variable placeholders
            variables: Dictionary mapping variable names to values
            strict: If True, raise error for missing variables; if False, leave unreplaced

        Returns:
            Resolved template text

        Raises:
            MissingVariableError: If strict=True and a required variable is missing
            ResolutionError: If resolution fails for other reasons

        Example:
            >>> resolver = TemplateResolver()
            >>> resolver.resolve_template(
            ...     "Hello {name}",
            ...     {"name": "World"}
            ... )
            'Hello World'
        """
        # Validate template
        is_valid, errors = self.parser.validate_template(template_text)
        if not is_valid:
            raise ResolutionError(f"Invalid template: {'; '.join(errors)}")

        # Extract variables from template
        template_vars = self.parser.extract_variables(template_text)

        # Check for missing variables
        if strict:
            missing_vars = [var for var in template_vars if var not in variables]
            if missing_vars:
                raise MissingVariableError(
                    f"Missing required variables: {', '.join(missing_vars)}"
                )

        # Resolve template
        result = template_text
        for var_name, var_value in variables.items():
            placeholder = f"{self.parser.delimiter.start}{var_name}{self.parser.delimiter.end}"
            result = result.replace(placeholder, str(var_value))

        return result

    def resolve_prompt(
        self,
        prompt: Prompt,
        variables: Dict[str, str],
        strict: bool = True
    ) -> str:
        """
        Resolve a Prompt object with variables.

        Args:
            prompt: Prompt object to resolve
            variables: Variable values
            strict: If True, raise error for missing variables

        Returns:
            Resolved prompt text

        Raises:
            MissingVariableError: If strict=True and a required variable is missing
        """
        # Load prompt content if not cached
        content = prompt.get_content(self.base_path)

        # Resolve variables
        return self.resolve_template(content, variables, strict=strict)

    def resolve_template_object(
        self,
        template: Template,
        additional_vars: Optional[Dict[str, str]] = None,
        strict: bool = True
    ) -> Dict[PromptRole, str]:
        """
        Resolve a complete Template object with all prompts.

        Args:
            template: Template object to resolve
            additional_vars: Additional variable values (merged with template variables)
            strict: If True, raise error for missing variables

        Returns:
            Dictionary mapping PromptRole to resolved prompt text

        Raises:
            MissingVariableError: If strict=True and a required variable is missing
        """
        # Build complete variables dictionary
        variables = template.get_all_variables_dict(self.base_path)

        # Merge with additional variables if provided
        if additional_vars:
            variables.update(additional_vars)

        # Resolve each prompt
        resolved_prompts = {}
        for role, prompt in template.prompts.items():
            resolved_prompts[role] = self.resolve_prompt(prompt, variables, strict=strict)

        return resolved_prompts

    def get_missing_variables(
        self,
        template_text: str,
        provided_variables: Dict[str, str]
    ) -> List[str]:
        """
        Get list of variables required by template but not provided.

        Args:
            template_text: Template text
            provided_variables: Variables that are provided

        Returns:
            List of missing variable names
        """
        template_vars = self.parser.extract_variables(template_text)
        return [var for var in template_vars if var not in provided_variables]

    def get_unused_variables(
        self,
        template_text: str,
        provided_variables: Dict[str, str]
    ) -> List[str]:
        """
        Get list of provided variables that are not used in template.

        Args:
            template_text: Template text
            provided_variables: Variables that are provided

        Returns:
            List of unused variable names
        """
        template_vars = set(self.parser.extract_variables(template_text))
        return [var for var in provided_variables if var not in template_vars]

    def preview_resolution(
        self,
        template_text: str,
        variables: Dict[str, str]
    ) -> Tuple[str, Dict[str, List[str]]]:
        """
        Preview template resolution with diagnostic information.

        Args:
            template_text: Template text
            variables: Variable values

        Returns:
            Tuple of (resolved_text, diagnostics)
            where diagnostics contains 'missing' and 'unused' variable lists
        """
        missing = self.get_missing_variables(template_text, variables)
        unused = self.get_unused_variables(template_text, variables)

        try:
            resolved = self.resolve_template(template_text, variables, strict=False)
        except Exception as e:
            resolved = f"ERROR: {str(e)}"

        diagnostics = {
            "missing": missing,
            "unused": unused
        }

        return (resolved, diagnostics)


class VariableResolver:
    """
    Resolves Variable objects to their actual values.

    Handles loading from files and managing base paths.
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize variable resolver.

        Args:
            base_path: Base directory for resolving relative file paths
        """
        self.base_path = base_path or Path.cwd()

    def resolve_variable(self, variable: Variable) -> str:
        """
        Resolve a single variable to its value.

        Args:
            variable: Variable object to resolve

        Returns:
            Variable value

        Raises:
            FileNotFoundError: If file variable references non-existent file
            ResolutionError: If resolution fails
        """
        try:
            return variable.resolve(self.base_path)
        except Exception as e:
            raise ResolutionError(f"Error resolving variable '{variable.name}': {e}")

    def resolve_variables(self, variables: Dict[str, Variable]) -> Dict[str, str]:
        """
        Resolve multiple variables to their values.

        Args:
            variables: Dictionary of Variable objects

        Returns:
            Dictionary mapping variable names to resolved values

        Raises:
            ResolutionError: If any variable resolution fails
        """
        result = {}
        errors = []

        for name, var in variables.items():
            try:
                result[name] = self.resolve_variable(var)
            except Exception as e:
                errors.append(f"{name}: {str(e)}")

        if errors:
            raise ResolutionError(
                f"Failed to resolve {len(errors)} variable(s):\n" + "\n".join(errors)
            )

        return result


def resolve_template(
    template_text: str,
    variables: Dict[str, str],
    start_delimiter: str = "{",
    end_delimiter: str = "}",
    strict: bool = True
) -> str:
    """
    Convenience function to resolve a template with variables.

    Args:
        template_text: Template text with placeholders
        variables: Variable values
        start_delimiter: Opening delimiter (default: "{")
        end_delimiter: Closing delimiter (default: "}")
        strict: If True, raise error for missing variables

    Returns:
        Resolved template text

    Raises:
        MissingVariableError: If strict=True and variables are missing
        ResolutionError: If resolution fails
    """
    delimiter = DelimiterConfig(start_delimiter, end_delimiter)
    resolver = TemplateResolver(delimiter=delimiter)
    return resolver.resolve_template(template_text, variables, strict=strict)
