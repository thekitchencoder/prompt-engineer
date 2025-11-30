#!/usr/bin/env python3
"""
Test script for the new modular architecture.

Verifies that all core modules can be imported and basic functionality works.
"""

import sys
from pathlib import Path

# Add src to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        # Config module
        from prompt_engineer.config.settings import (
            AppSettings,
            ConfigManager,
            ProviderPresets
        )
        print("  ✓ Config module")

        # Providers module
        from prompt_engineer.providers.base import (
            LLMProvider,
            LLMRequest,
            LLMResponse,
            Message,
            MessageRole
        )
        from prompt_engineer.providers.openai import OpenAIProvider
        from prompt_engineer.providers.registry import (
            create_provider,
            get_provider_registry
        )
        print("  ✓ Providers module")

        # Templates module
        from prompt_engineer.templates.models import (
            Template,
            Variable,
            Prompt,
            VariableType,
            PromptRole
        )
        from prompt_engineer.templates.parser import (
            TemplateParser,
            DelimiterConfig
        )
        from prompt_engineer.templates.resolver import (
            TemplateResolver,
            resolve_template
        )
        print("  ✓ Templates module")

        # Workspace module
        from prompt_engineer.workspace.config import (
            WorkspaceConfig,
            WorkspacePresets
        )
        from prompt_engineer.workspace.discovery import (
            WorkspaceDiscovery,
            ProjectDetector
        )
        from prompt_engineer.workspace.workspace import (
            Workspace,
            WorkspaceManager
        )
        print("  ✓ Workspace module")

        print("\n✅ All imports successful!\n")
        return True

    except ImportError as e:
        print(f"\n❌ Import failed: {e}\n")
        return False


def test_template_parser():
    """Test template parser functionality."""
    print("Testing template parser...")

    from prompt_engineer.templates.parser import TemplateParser

    parser = TemplateParser()

    # Test variable extraction
    template = "Hello {name}, your code: {code}"
    variables = parser.extract_variables(template)

    assert variables == ["name", "code"], f"Expected ['name', 'code'], got {variables}"
    print(f"  ✓ Extract variables: {variables}")

    # Test validation
    valid, errors = parser.validate_template(template)
    assert valid, f"Template should be valid, got errors: {errors}"
    print("  ✓ Template validation")

    print()


def test_template_resolver():
    """Test template resolver functionality."""
    print("Testing template resolver...")

    from prompt_engineer.templates.resolver import resolve_template

    template = "Hello {name}, welcome to {place}!"
    variables = {
        "name": "Alice",
        "place": "Wonderland"
    }

    result = resolve_template(template, variables)
    expected = "Hello Alice, welcome to Wonderland!"

    assert result == expected, f"Expected '{expected}', got '{result}'"
    print(f"  ✓ Resolved template: {result}")

    print()


def test_config_management():
    """Test configuration management."""
    print("Testing configuration management...")

    from prompt_engineer.config.settings import ProviderPresets

    # Test provider presets
    openai_preset = ProviderPresets.OPENAI
    assert openai_preset.base_url == "", "OpenAI should have empty base_url"
    assert openai_preset.api_key_required is True
    print(f"  ✓ OpenAI preset: {openai_preset.default_models}")

    ollama_preset = ProviderPresets.OLLAMA
    assert "localhost:11434" in ollama_preset.base_url
    assert ollama_preset.api_key_required is False
    print(f"  ✓ Ollama preset: {ollama_preset.base_url}")

    print()


def test_workspace_presets():
    """Test workspace presets."""
    print("Testing workspace presets...")

    from prompt_engineer.workspace.config import WorkspacePresets

    # Test SpringBoot preset
    springboot = WorkspacePresets.springboot()
    assert "src/main/resources/prompts" in springboot.layout.prompt_dir
    assert springboot.layout.prompt_extension == ".st"
    print(f"  ✓ SpringBoot preset: {springboot.layout.prompt_dir}")

    # Test Python preset
    python = WorkspacePresets.python()
    assert "app/prompts" in python.layout.prompt_dir
    assert python.layout.prompt_extension == ".txt"
    print(f"  ✓ Python preset: {python.layout.prompt_dir}")

    print()


def test_provider_registry():
    """Test provider registry."""
    print("Testing provider registry...")

    from prompt_engineer.providers.registry import get_provider_registry

    registry = get_provider_registry()

    # Test listing providers
    providers = registry.list_providers()
    assert "openai" in providers
    assert "ollama" in providers
    print(f"  ✓ Available providers: {', '.join(providers)}")

    # Test creating a provider
    provider = registry.create_provider(
        "openai",
        api_key="test-key",
        base_url=None
    )
    assert provider is not None
    assert provider.provider_name == "OpenAI"
    print(f"  ✓ Created provider: {provider.provider_name}")

    print()


def test_template_models():
    """Test template data models."""
    print("Testing template models...")

    from prompt_engineer.templates.models import (
        Variable,
        Prompt,
        Template,
        VariableType,
        PromptRole
    )

    # Create a variable
    var = Variable.from_value("name", "Alice", "User's name")
    assert var.name == "name"
    assert var.type == VariableType.VALUE
    print(f"  ✓ Created variable: {var.name}")

    # Create a template
    template = Template(name="test-template", description="Test template")
    template.add_variable(var)

    assert template.has_variable("name")
    assert template.get_variable("name") == var
    print(f"  ✓ Created template: {template.name}")

    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Prompt Engineer Modular Architecture")
    print("=" * 60)
    print()

    # Test imports first
    if not test_imports():
        print("❌ Import tests failed. Cannot proceed with other tests.")
        return 1

    # Run functionality tests
    try:
        test_template_parser()
        test_template_resolver()
        test_config_management()
        test_workspace_presets()
        test_provider_registry()
        test_template_models()

        print("=" * 60)
        print("✅ All tests passed successfully!")
        print("=" * 60)
        print()
        print("The modular architecture is working correctly.")
        print("You can now proceed with building the UI and integrating")
        print("these components into the main application.")
        print()

        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
