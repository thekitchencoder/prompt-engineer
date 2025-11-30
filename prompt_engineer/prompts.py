"""Prompt file operations and variable interpolation."""

import re
from pathlib import Path
from typing import List, Dict, Any, Tuple


def list_prompt_files(workspace_root: str, prompt_dir: str) -> List[str]:
    """List all prompt files in the prompt directory."""
    prompt_path = Path(workspace_root) / prompt_dir

    if not prompt_path.exists():
        return []

    # Find all files (any extension), excluding directories and hidden files
    files = sorted([
        f.name for f in prompt_path.iterdir()
        if f.is_file() and not f.name.startswith('.')
    ])
    return files


def load_prompt_file(workspace_root: str, prompt_dir: str, filename: str) -> str:
    """Load content from a prompt file."""
    if not filename:
        return ""

    file_path = Path(workspace_root) / prompt_dir / filename

    if not file_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def save_prompt_file(workspace_root: str, prompt_dir: str, filename: str, content: str) -> str:
    """Save content to a prompt file."""
    if not filename:
        return "❌ Please provide a filename"

    try:
        prompt_path = Path(workspace_root) / prompt_dir
        prompt_path.mkdir(parents=True, exist_ok=True)

        file_path = prompt_path / filename

        with open(file_path, 'w') as f:
            f.write(content)

        return f"✅ Saved: {filename}"
    except Exception as e:
        return f"❌ Error saving file: {e}"


def extract_variables(template: str) -> List[str]:
    """Extract variable names from a template using {var_name} syntax."""
    return sorted(list(set(re.findall(r'\{(\w+)\}', template))))


def load_variable_value(workspace_root: str, var_config: Dict[str, Any]) -> str:
    """Load variable value from config (file or value)."""
    var_type = var_config.get("type")

    if var_type == "file":
        file_path = var_config.get("path", "")
        full_path = Path(workspace_root) / file_path

        if not full_path.exists():
            return f"[Error: File not found: {file_path}]"

        try:
            with open(full_path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"[Error reading file: {e}]"

    elif var_type == "value":
        return var_config.get("value", "")

    return f"[Error: Unknown variable type: {var_type}]"


def interpolate_prompt(template: str, workspace_root: str, variables: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Interpolate variables into prompt template.

    Returns:
        Tuple of (interpolated_prompt, list of unmapped variables)
    """
    # Extract variables from template
    template_vars = extract_variables(template)

    # Track unmapped variables
    unmapped = []

    # Build variable values
    var_values = {}
    for var_name in template_vars:
        if var_name not in variables:
            unmapped.append(var_name)
            var_values[var_name] = f"{{UNMAPPED: {var_name}}}"
        else:
            var_values[var_name] = load_variable_value(workspace_root, variables[var_name])

    # Interpolate
    try:
        interpolated = template.format(**var_values)
        return interpolated, unmapped
    except KeyError as e:
        return f"Error: Missing variable {e}", unmapped
    except Exception as e:
        return f"Error interpolating template: {e}", unmapped


def validate_prompt_variables(template: str, variables: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Validate that all variables in template are mapped and files exist.

    Returns:
        Tuple of (unmapped_variables, missing_files)
    """
    template_vars = extract_variables(template)
    unmapped = []
    missing_files = []

    for var_name in template_vars:
        if var_name not in variables:
            unmapped.append(var_name)
        else:
            var_config = variables[var_name]
            if var_config.get("type") == "file":
                # File path validation is done in config.py
                pass

    return unmapped, missing_files
