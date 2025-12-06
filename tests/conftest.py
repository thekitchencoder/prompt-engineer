"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_user_config_dir(monkeypatch):
    """Create a temporary user config directory for testing."""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir) / ".prompt-engineer"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Monkeypatch the USER_CONFIG_DIR and USER_CONFIG_FILE
    from prompt_engineer import config
    monkeypatch.setattr(config, 'USER_CONFIG_DIR', config_dir)
    monkeypatch.setattr(config, 'USER_CONFIG_FILE', config_dir / "config.yaml")

    yield config_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_prompt_files(temp_workspace):
    """Create sample prompt files in workspace."""
    prompts_dir = Path(temp_workspace) / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Create root-level prompts
    (prompts_dir / "system.txt").write_text("You are a helpful assistant.")
    (prompts_dir / "user_query.txt").write_text("Analyze {code} and explain {concept}.")

    # Create nested prompts
    nested_dir = prompts_dir / "templates"
    nested_dir.mkdir(exist_ok=True)
    (nested_dir / "analysis.txt").write_text("Deep analysis of {topic}.")

    # Create hidden file (should be excluded)
    (prompts_dir / ".hidden.txt").write_text("Hidden content")

    yield prompts_dir


@pytest.fixture
def sample_variable_files(temp_workspace):
    """Create sample variable files in workspace."""
    data_dir = Path(temp_workspace) / "prompt-data"
    data_dir.mkdir(exist_ok=True)

    (data_dir / "code.py").write_text("def hello():\n    print('world')")
    (data_dir / "concept.txt").write_text("recursion")

    yield data_dir
