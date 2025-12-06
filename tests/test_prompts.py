"""Unit tests for prompts.py."""

import pytest
from pathlib import Path
from prompt_engineer import prompts


class TestListPromptFiles:
    """Tests for listing prompt files."""

    def test_list_empty_directory(self, temp_workspace):
        """Test listing prompts in empty directory."""
        prompts_dir = Path(temp_workspace) / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        files = prompts.list_prompt_files(temp_workspace, "prompts")
        assert files == []

    def test_list_nonexistent_directory(self, temp_workspace):
        """Test listing prompts when directory doesn't exist."""
        files = prompts.list_prompt_files(temp_workspace, "nonexistent")
        assert files == []

    def test_list_prompt_files_root_only(self, temp_workspace):
        """Test listing prompt files at root level."""
        prompts_dir = Path(temp_workspace) / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        (prompts_dir / "system.txt").write_text("System prompt")
        (prompts_dir / "user.txt").write_text("User prompt")

        files = prompts.list_prompt_files(temp_workspace, "prompts")

        assert len(files) == 2
        assert "system.txt" in files
        assert "user.txt" in files

    def test_list_prompt_files_with_nested(self, temp_workspace, sample_prompt_files):
        """Test listing prompt files with nested directories."""
        files = prompts.list_prompt_files(temp_workspace, "prompts")

        # Should include root-level and nested files
        assert "system.txt" in files
        assert "user_query.txt" in files
        assert "templates/analysis.txt" in files

        # Should NOT include hidden files
        assert ".hidden.txt" not in files

    def test_list_prompt_files_sorting(self, temp_workspace, sample_prompt_files):
        """Test that root-level files come before nested files."""
        files = prompts.list_prompt_files(temp_workspace, "prompts")

        # Find index of root-level and nested files
        root_indices = [i for i, f in enumerate(files) if "/" not in f]
        nested_indices = [i for i, f in enumerate(files) if "/" in f]

        # All root files should come before all nested files
        if root_indices and nested_indices:
            assert max(root_indices) < min(nested_indices)

    def test_list_excludes_directories(self, temp_workspace):
        """Test that directories are excluded from file list."""
        prompts_dir = Path(temp_workspace) / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        (prompts_dir / "subdir").mkdir(exist_ok=True)
        (prompts_dir / "file.txt").write_text("Content")

        files = prompts.list_prompt_files(temp_workspace, "prompts")

        assert "file.txt" in files
        assert "subdir" not in files


class TestLoadAndSavePromptFiles:
    """Tests for loading and saving prompt files."""

    def test_load_existing_file(self, temp_workspace, sample_prompt_files):
        """Test loading an existing prompt file."""
        content = prompts.load_prompt_file(temp_workspace, "prompts", "system.txt")
        assert content == "You are a helpful assistant."

    def test_load_nonexistent_file(self, temp_workspace):
        """Test loading a nonexistent file returns error."""
        content = prompts.load_prompt_file(temp_workspace, "prompts", "missing.txt")
        assert "Error" in content or "not found" in content.lower()

    def test_load_empty_filename(self, temp_workspace):
        """Test loading with empty filename returns empty string."""
        content = prompts.load_prompt_file(temp_workspace, "prompts", "")
        assert content == ""

    def test_load_nested_file(self, temp_workspace, sample_prompt_files):
        """Test loading a nested prompt file."""
        content = prompts.load_prompt_file(temp_workspace, "prompts", "templates/analysis.txt")
        assert content == "Deep analysis of {topic}."

    def test_save_new_file(self, temp_workspace):
        """Test saving a new prompt file."""
        prompts_dir = Path(temp_workspace) / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        result = prompts.save_prompt_file(temp_workspace, "prompts", "new.txt", "New content")

        assert "✅" in result or "Saved" in result
        assert (prompts_dir / "new.txt").exists()
        assert (prompts_dir / "new.txt").read_text() == "New content"

    def test_save_nested_file_creates_directories(self, temp_workspace):
        """Test saving nested file creates parent directories."""
        prompts_dir = Path(temp_workspace) / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        result = prompts.save_prompt_file(
            temp_workspace,
            "prompts",
            "nested/deep/file.txt",
            "Nested content"
        )

        assert "✅" in result or "Saved" in result
        file_path = prompts_dir / "nested" / "deep" / "file.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Nested content"

    def test_save_empty_filename(self, temp_workspace):
        """Test saving with empty filename returns error."""
        result = prompts.save_prompt_file(temp_workspace, "prompts", "", "Content")
        assert "❌" in result or "filename" in result.lower()

    def test_save_overwrites_existing(self, temp_workspace, sample_prompt_files):
        """Test saving overwrites existing file."""
        result = prompts.save_prompt_file(
            temp_workspace,
            "prompts",
            "system.txt",
            "Updated content"
        )

        assert "✅" in result or "Saved" in result
        content = prompts.load_prompt_file(temp_workspace, "prompts", "system.txt")
        assert content == "Updated content"


class TestVariableExtraction:
    """Tests for variable extraction from templates."""

    def test_extract_no_variables(self):
        """Test extracting variables from template with none."""
        template = "This is a plain prompt with no variables."
        variables = prompts.extract_variables(template)
        assert variables == []

    def test_extract_single_variable(self):
        """Test extracting a single variable."""
        template = "Analyze {code} for issues."
        variables = prompts.extract_variables(template)
        assert variables == ["code"]

    def test_extract_multiple_variables(self):
        """Test extracting multiple variables."""
        template = "Compare {code} with {reference} and explain {concept}."
        variables = prompts.extract_variables(template)
        assert set(variables) == {"code", "reference", "concept"}

    def test_extract_duplicate_variables(self):
        """Test extracting duplicate variables returns unique list."""
        template = "Analyze {code} and test {code} for {issue}."
        variables = prompts.extract_variables(template)
        assert variables.count("code") == 1
        assert "issue" in variables

    def test_extract_variables_sorted(self):
        """Test extracted variables are sorted."""
        template = "Show {zebra} then {apple} then {banana}."
        variables = prompts.extract_variables(template)
        assert variables == ["apple", "banana", "zebra"]

    def test_extract_ignores_invalid_braces(self):
        """Test extraction ignores invalid brace patterns."""
        template = "Valid {var} but not { spaces } or {123numbers} or {}"
        variables = prompts.extract_variables(template)
        # Should only extract valid variable names (alphanumeric + underscore)
        assert "var" in variables


class TestVariableLoading:
    """Tests for loading variable values."""

    def test_load_variable_value_file(self, temp_workspace, sample_variable_files):
        """Test loading variable from file."""
        var_config = {
            "type": "file",
            "path": "prompt-data/code.py"
        }

        value = prompts.load_variable_value(temp_workspace, var_config)
        assert "def hello():" in value
        assert "print('world')" in value

    def test_load_variable_value_nonexistent_file(self, temp_workspace):
        """Test loading variable from nonexistent file returns error."""
        var_config = {
            "type": "file",
            "path": "missing.txt"
        }

        value = prompts.load_variable_value(temp_workspace, var_config)
        assert "Error" in value or "not found" in value.lower()

    def test_load_variable_value_inline(self, temp_workspace):
        """Test loading inline variable value."""
        var_config = {
            "type": "value",
            "value": "inline text content"
        }

        value = prompts.load_variable_value(temp_workspace, var_config)
        assert value == "inline text content"

    def test_load_variable_unknown_type(self, temp_workspace):
        """Test loading variable with unknown type returns error."""
        var_config = {
            "type": "unknown",
            "value": "test"
        }

        value = prompts.load_variable_value(temp_workspace, var_config)
        assert "Error" in value or "Unknown" in value


class TestPromptInterpolation:
    """Tests for prompt interpolation."""

    def test_interpolate_no_variables(self, temp_workspace):
        """Test interpolating template with no variables."""
        template = "Plain text prompt."
        interpolated, unmapped = prompts.interpolate_prompt(template, temp_workspace, {})

        assert interpolated == template
        assert unmapped == []

    def test_interpolate_with_file_variable(self, temp_workspace, sample_variable_files):
        """Test interpolating with file-based variable."""
        template = "Analyze this code:\n{code}"
        variables = {
            "code": {
                "type": "file",
                "path": "prompt-data/code.py"
            }
        }

        interpolated, unmapped = prompts.interpolate_prompt(template, temp_workspace, variables)

        assert "def hello():" in interpolated
        assert unmapped == []

    def test_interpolate_with_inline_variable(self, temp_workspace):
        """Test interpolating with inline value variable."""
        template = "Explain {concept} in detail."
        variables = {
            "concept": {
                "type": "value",
                "value": "recursion"
            }
        }

        interpolated, unmapped = prompts.interpolate_prompt(template, temp_workspace, variables)

        assert interpolated == "Explain recursion in detail."
        assert unmapped == []

    def test_interpolate_multiple_variables(self, temp_workspace, sample_variable_files):
        """Test interpolating with multiple variables."""
        template = "Analyze {code} and explain {concept}."
        variables = {
            "code": {
                "type": "file",
                "path": "prompt-data/code.py"
            },
            "concept": {
                "type": "value",
                "value": "functions"
            }
        }

        interpolated, unmapped = prompts.interpolate_prompt(template, temp_workspace, variables)

        assert "def hello():" in interpolated
        assert "functions" in interpolated
        assert unmapped == []

    def test_interpolate_unmapped_variable(self, temp_workspace):
        """Test interpolating with unmapped variable."""
        template = "Analyze {code} for {issue}."
        variables = {
            "code": {
                "type": "value",
                "value": "test code"
            }
        }

        interpolated, unmapped = prompts.interpolate_prompt(template, temp_workspace, variables)

        assert "test code" in interpolated
        assert "UNMAPPED: issue" in interpolated
        assert unmapped == ["issue"]

    def test_interpolate_all_unmapped(self, temp_workspace):
        """Test interpolating with all variables unmapped."""
        template = "Show {var1} and {var2}."
        variables = {}

        interpolated, unmapped = prompts.interpolate_prompt(template, temp_workspace, variables)

        assert set(unmapped) == {"var1", "var2"}
        assert "UNMAPPED" in interpolated


class TestValidatePromptVariables:
    """Tests for validating prompt variables."""

    def test_validate_no_variables(self):
        """Test validating template with no variables."""
        template = "Plain text."
        unmapped, missing = prompts.validate_prompt_variables(template, {})

        assert unmapped == []
        assert missing == []

    def test_validate_all_mapped(self):
        """Test validating template with all variables mapped."""
        template = "Show {var1} and {var2}."
        variables = {
            "var1": {"type": "value", "value": "test"},
            "var2": {"type": "value", "value": "test"}
        }

        unmapped, missing = prompts.validate_prompt_variables(template, variables)

        assert unmapped == []

    def test_validate_unmapped_variables(self):
        """Test validating template with unmapped variables."""
        template = "Show {var1} and {var2}."
        variables = {
            "var1": {"type": "value", "value": "test"}
        }

        unmapped, missing = prompts.validate_prompt_variables(template, variables)

        assert unmapped == ["var2"]
