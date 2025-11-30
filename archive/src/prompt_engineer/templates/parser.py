"""
Template parser with configurable variable delimiter support.

Extracts variable names from template text using customizable delimiters.
"""

import re
from typing import List, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DelimiterConfig:
    """Configuration for variable delimiters."""

    start: str = "{"
    end: str = "}"

    def __post_init__(self):
        """Validate delimiter configuration."""
        if not self.start or not self.end:
            raise ValueError("Delimiters cannot be empty")

    def __str__(self) -> str:
        """String representation."""
        return f"{self.start}variable{self.end}"


class TemplateParser:
    """
    Parser for extracting variables from prompt templates.

    Supports configurable delimiters to work with different template systems
    (Spring, StringTemplate, Jinja2, etc.).
    """

    # Common delimiter presets
    PRESETS = {
        "curly": DelimiterConfig("{", "}"),           # {var} - Python, Spring, Jinja2
        "dollar": DelimiterConfig("$", "$"),          # $var$ - StringTemplate
        "angle": DelimiterConfig("<", ">"),           # <var> - StringTemplate
        "double_bracket": DelimiterConfig("[[", "]]"), # [[var]] - MediaWiki
        "shell": DelimiterConfig("${", "}"),          # ${var} - Shell, Spring EL
    }

    def __init__(self, delimiter: Optional[DelimiterConfig] = None):
        """
        Initialize parser with delimiter configuration.

        Args:
            delimiter: Delimiter configuration (defaults to {})
        """
        self.delimiter = delimiter or DelimiterConfig()

    @classmethod
    def with_preset(cls, preset_name: str) -> "TemplateParser":
        """
        Create parser with a preset delimiter configuration.

        Args:
            preset_name: Name of preset ("curly", "dollar", "angle", etc.)

        Returns:
            TemplateParser instance

        Raises:
            ValueError: If preset name is unknown
        """
        if preset_name not in cls.PRESETS:
            raise ValueError(
                f"Unknown preset '{preset_name}'. "
                f"Available presets: {', '.join(cls.PRESETS.keys())}"
            )

        return cls(delimiter=cls.PRESETS[preset_name])

    @classmethod
    def with_delimiters(cls, start: str, end: str) -> "TemplateParser":
        """
        Create parser with custom delimiters.

        Args:
            start: Start delimiter
            end: End delimiter

        Returns:
            TemplateParser instance
        """
        return cls(delimiter=DelimiterConfig(start, end))

    def extract_variables(self, template: str) -> List[str]:
        """
        Extract variable names from template.

        Args:
            template: Template text with variable placeholders

        Returns:
            List of unique variable names (in order of first appearance)

        Example:
            >>> parser = TemplateParser()
            >>> parser.extract_variables("Hello {name}, your code: {code}")
            ['name', 'code']
        """
        # Escape special regex characters
        start_escaped = re.escape(self.delimiter.start)
        end_escaped = re.escape(self.delimiter.end)

        # Pattern: {start}word_chars{end}
        # Matches one or more word characters (letters, digits, underscores)
        pattern = f'{start_escaped}(\\w+){end_escaped}'

        # Find all matches
        matches = re.findall(pattern, template)

        # Return unique variables in order of first appearance
        seen: Set[str] = set()
        result: List[str] = []

        for var in matches:
            if var not in seen:
                seen.add(var)
                result.append(var)

        return result

    def find_variables_with_positions(self, template: str) -> List[Tuple[str, int, int]]:
        """
        Find variables with their positions in the template.

        Args:
            template: Template text

        Returns:
            List of tuples (variable_name, start_pos, end_pos)

        Example:
            >>> parser = TemplateParser()
            >>> parser.find_variables_with_positions("Hello {name}")
            [('name', 6, 12)]
        """
        start_escaped = re.escape(self.delimiter.start)
        end_escaped = re.escape(self.delimiter.end)
        pattern = f'{start_escaped}(\\w+){end_escaped}'

        results = []
        for match in re.finditer(pattern, template):
            var_name = match.group(1)
            start_pos = match.start()
            end_pos = match.end()
            results.append((var_name, start_pos, end_pos))

        return results

    def validate_template(self, template: str) -> Tuple[bool, List[str]]:
        """
        Validate template syntax.

        Checks for:
        - Unmatched delimiters
        - Empty variable names
        - Invalid variable names (non-word characters)

        Args:
            template: Template text to validate

        Returns:
            Tuple of (is_valid, list_of_errors)

        Example:
            >>> parser = TemplateParser()
            >>> parser.validate_template("{valid} {also_valid}")
            (True, [])
            >>> parser.validate_template("{unclosed")
            (False, ['Unmatched opening delimiter at position 0'])
        """
        errors = []

        # Check for unmatched delimiters
        start_count = template.count(self.delimiter.start)
        end_count = template.count(self.delimiter.end)

        if start_count != end_count:
            errors.append(
                f"Mismatched delimiters: {start_count} opening, {end_count} closing"
            )

        # Check for empty or invalid variable names
        start_escaped = re.escape(self.delimiter.start)
        end_escaped = re.escape(self.delimiter.end)

        # Pattern for empty variables: {start}{end}
        empty_pattern = f'{start_escaped}{end_escaped}'
        if re.search(empty_pattern, template):
            errors.append("Found empty variable placeholder (no name)")

        # Pattern for invalid variable names: {start}non_word_chars{end}
        invalid_pattern = f'{start_escaped}([^\\w]+){end_escaped}'
        invalid_matches = re.findall(invalid_pattern, template)
        if invalid_matches:
            errors.append(
                f"Invalid variable names (must be alphanumeric + underscore): "
                f"{', '.join(invalid_matches)}"
            )

        return (len(errors) == 0, errors)

    def has_variables(self, template: str) -> bool:
        """
        Check if template contains any variables.

        Args:
            template: Template text

        Returns:
            True if template has variables, False otherwise
        """
        return len(self.extract_variables(template)) > 0

    def count_variables(self, template: str) -> int:
        """
        Count total number of variable occurrences (including duplicates).

        Args:
            template: Template text

        Returns:
            Number of variable placeholders
        """
        start_escaped = re.escape(self.delimiter.start)
        end_escaped = re.escape(self.delimiter.end)
        pattern = f'{start_escaped}\\w+{end_escaped}'

        return len(re.findall(pattern, template))

    def escape_literal(self, text: str) -> str:
        """
        Escape delimiter characters in text so they're treated as literals.

        Args:
            text: Text to escape

        Returns:
            Escaped text

        Example:
            >>> parser = TemplateParser()
            >>> parser.escape_literal("Use {curly braces}")
            "Use \\{curly braces\\}"
        """
        result = text.replace(self.delimiter.start, f"\\{self.delimiter.start}")
        result = result.replace(self.delimiter.end, f"\\{self.delimiter.end}")
        return result

    def get_delimiter_info(self) -> str:
        """
        Get human-readable delimiter information.

        Returns:
            String describing current delimiter configuration
        """
        return f"Variables use {self.delimiter} format"


def extract_variables(template: str, start_delimiter: str = "{", end_delimiter: str = "}") -> List[str]:
    """
    Convenience function to extract variables from a template.

    Args:
        template: Template text
        start_delimiter: Opening delimiter (default: "{")
        end_delimiter: Closing delimiter (default: "}")

    Returns:
        List of variable names
    """
    parser = TemplateParser.with_delimiters(start_delimiter, end_delimiter)
    return parser.extract_variables(template)


def validate_template(template: str, start_delimiter: str = "{", end_delimiter: str = "}") -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a template.

    Args:
        template: Template text
        start_delimiter: Opening delimiter (default: "{")
        end_delimiter: Closing delimiter (default: "}")

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    parser = TemplateParser.with_delimiters(start_delimiter, end_delimiter)
    return parser.validate_template(template)
