"""Prompt Engineer - Main Gradio UI Application."""

import os
import argparse
import gradio as gr
from pathlib import Path
from typing import Dict, Any, List

from .config import (
    load_user_config,
    save_user_config,
    load_workspace_config,
    save_workspace_config,
    validate_user_config,
    validate_workspace_config,
)
from .prompts import (
    list_prompt_files,
    load_prompt_file,
    save_prompt_file,
    extract_variables,
    interpolate_prompt,
)
from .llm import (
    fetch_available_models,
    call_llm_api,
    estimate_tokens,
    estimate_cost,
)


# Global state
WORKSPACE_ROOT = os.getcwd()


def get_workspace_root() -> str:
    """Get current workspace root."""
    return WORKSPACE_ROOT


def set_workspace_root(path: str):
    """Set workspace root."""
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = path


# ============================================================================
# Section 1: User Config
# ============================================================================


def load_user_config_ui() -> tuple:
    """Load user config and populate UI."""
    config = load_user_config()

    provider = config.get("provider", "openai")
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")
    models = config.get("models", [])
    defaults = config.get("defaults", {})

    return (
        provider,
        api_key,
        base_url,
        models,
        defaults.get("model", "gpt-4o"),
        defaults.get("temperature", 0.7),
        defaults.get("max_tokens", 2000),
    )


def update_provider_preset(provider: str) -> tuple:
    """Update config fields based on provider preset."""
    config = load_user_config()
    presets = config.get("presets", {})
    preset = presets.get(provider, {})

    base_url = preset.get("base_url", "")
    default_models = preset.get("default_models", [])

    return (
        base_url,
        gr.update(choices=default_models, value=default_models),
        gr.update(choices=default_models, value=default_models[0] if default_models else ""),
        "",
    )


def load_models_from_provider(api_key: str, base_url: str) -> tuple:
    """Fetch models from provider API."""
    if not api_key and not base_url:
        return (
            gr.update(choices=[]),
            "⚠️ Please configure API key or base URL first",
            gr.update(choices=[]),
        )

    success, result = fetch_available_models(api_key, base_url or None)

    if success:
        return (
            gr.update(choices=result, value=result),
            f"✅ Loaded {len(result)} models",
            gr.update(choices=result, value=result[0] if result else ""),
        )
    else:
        return (
            gr.update(choices=[]),
            f"❌ {result}",
            gr.update(choices=[]),
        )


def save_user_config_ui(
    provider: str,
    api_key: str,
    base_url: str,
    models: List[str],
    default_model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Save user configuration."""
    config = load_user_config()

    config["provider"] = provider
    config["api_key"] = api_key
    config["base_url"] = base_url
    config["models"] = models
    config["defaults"]["model"] = default_model
    config["defaults"]["temperature"] = temperature
    config["defaults"]["max_tokens"] = max_tokens

    return save_user_config(config)


# ============================================================================
# Section 2: Workspace Config
# ============================================================================


def load_workspace_config_ui() -> tuple:
    """Load workspace config and populate UI."""
    config = load_workspace_config(get_workspace_root())

    name = config.get("name", "My Workspace")
    paths = config.get("paths", {})
    prompt_dir = paths.get("prompts", "prompts")
    data_dir = paths.get("data", "prompt-data")

    # Build variable table data
    variables = config.get("variables", {})
    var_rows = []
    for var_name, var_config in variables.items():
        var_type = var_config.get("type", "value")
        if var_type == "file":
            source = var_config.get("path", "")
        else:
            value = var_config.get("value", "")
            source = value[:50] + "..." if len(value) > 50 else value
        var_rows.append([var_name, var_type, source])

    # Validation
    errors = validate_workspace_config(get_workspace_root(), config)
    if errors:
        status = "⚠️ Issues:\n" + "\n".join(f"  - {e}" for e in errors)
    else:
        status = f"✅ Workspace config valid ({len(variables)} variables)"

    return name, prompt_dir, data_dir, var_rows, status


def save_workspace_config_ui(
    name: str,
    prompt_dir: str,
    data_dir: str,
) -> str:
    """Save workspace configuration."""
    config = load_workspace_config(get_workspace_root())

    config["name"] = name
    config["paths"]["prompts"] = prompt_dir
    config["paths"]["data"] = data_dir

    # Validate before saving
    errors = validate_workspace_config(get_workspace_root(), config)
    if errors:
        return "⚠️ Cannot save - fix errors first:\n" + "\n".join(f"  - {e}" for e in errors)

    return save_workspace_config(get_workspace_root(), config)


def add_variable_ui(var_name: str, var_type: str, var_source: str) -> tuple:
    """Add a new variable to workspace config."""
    if not var_name:
        return [], "⚠️ Variable name required"

    config = load_workspace_config(get_workspace_root())
    variables = config.get("variables", {})

    # Add variable
    if var_type == "file":
        variables[var_name] = {"type": "file", "path": var_source}
    else:
        variables[var_name] = {"type": "value", "value": var_source}

    config["variables"] = variables

    # Save
    result = save_workspace_config(get_workspace_root(), config)

    # Reload table
    _, _, _, var_rows, status = load_workspace_config_ui()

    return var_rows, result


def refresh_workspace_config() -> tuple:
    """Reload workspace config from disk."""
    return load_workspace_config_ui()


# ============================================================================
# Section 3: Prompt Editor
# ============================================================================


def refresh_prompt_list() -> tuple:
    """Refresh list of available prompt files."""
    config = load_workspace_config(get_workspace_root())
    prompt_dir = config.get("paths", {}).get("prompts", "prompts")

    files = list_prompt_files(get_workspace_root(), prompt_dir)

    if not files:
        return gr.update(choices=[], value=None), "ℹ️ No prompt files found"

    return gr.update(choices=files, value=files[0] if files else None), f"✅ Found {len(files)} prompt files"


def load_prompt_ui(filename: str) -> tuple:
    """Load prompt file into editor."""
    if not filename:
        return "", "", "⚠️ No file selected"

    config = load_workspace_config(get_workspace_root())
    prompt_dir = config.get("paths", {}).get("prompts", "prompts")

    content = load_prompt_file(get_workspace_root(), prompt_dir, filename)

    # Extract variables and check mapping
    variables = extract_variables(content)
    workspace_vars = config.get("variables", {})

    unmapped = [v for v in variables if v not in workspace_vars]

    if unmapped:
        status = f"⚠️ Unmapped variables: {', '.join(unmapped)}"
    else:
        status = f"✅ All variables mapped ({len(variables)}/{len(variables)})"

    # Generate interpolated preview
    interpolated, _ = interpolate_prompt(content, get_workspace_root(), workspace_vars)

    return content, interpolated, status


def save_prompt_ui(filename: str, content: str) -> str:
    """Save prompt file."""
    config = load_workspace_config(get_workspace_root())
    prompt_dir = config.get("paths", {}).get("prompts", "prompts")

    return save_prompt_file(get_workspace_root(), prompt_dir, filename, content)


def update_interpolated_preview(content: str) -> str:
    """Update interpolated preview when template changes."""
    config = load_workspace_config(get_workspace_root())
    workspace_vars = config.get("variables", {})

    interpolated, unmapped = interpolate_prompt(content, get_workspace_root(), workspace_vars)

    return interpolated


def validate_prompt_variables_ui(content: str) -> str:
    """Validate prompt variables and show status."""
    variables = extract_variables(content)
    config = load_workspace_config(get_workspace_root())
    workspace_vars = config.get("variables", {})

    unmapped = [v for v in variables if v not in workspace_vars]

    if unmapped:
        return f"⚠️ Unmapped variables: {', '.join(unmapped)}"
    elif variables:
        return f"✅ All variables mapped ({len(variables)}/{len(variables)})"
    else:
        return "ℹ️ No variables found"


# ============================================================================
# Section 4: LLM Interaction
# ============================================================================


def get_available_prompts() -> List[str]:
    """Get list of available prompt files for dropdowns."""
    config = load_workspace_config(get_workspace_root())
    prompt_dir = config.get("paths", {}).get("prompts", "prompts")
    files = list_prompt_files(get_workspace_root(), prompt_dir)
    return ["(none)"] + files


def run_prompt_ui(
    system_prompt_file: str,
    user_prompt_file: str,
    model_override: str,
    temperature: float,
    max_tokens: int,
) -> tuple:
    """Execute prompt and return formatted/raw responses."""
    # Load user config
    user_config = load_user_config()
    api_key = user_config.get("api_key", "")
    base_url = user_config.get("base_url", "")

    # Determine model
    model = model_override if model_override else user_config.get("defaults", {}).get("model", "gpt-4o")

    # Load workspace config
    workspace_config = load_workspace_config(get_workspace_root())
    prompt_dir = workspace_config.get("paths", {}).get("prompts", "prompts")
    workspace_vars = workspace_config.get("variables", {})

    # Build messages
    messages = []

    # System prompt
    if system_prompt_file and system_prompt_file != "(none)":
        system_content = load_prompt_file(get_workspace_root(), prompt_dir, system_prompt_file)
        system_interpolated, _ = interpolate_prompt(system_content, get_workspace_root(), workspace_vars)
        messages.append({"role": "system", "content": system_interpolated})

    # User prompt
    if not user_prompt_file or user_prompt_file == "(none)":
        return "❌ User prompt required", {}, {}, "❌ User prompt required"

    user_content = load_prompt_file(get_workspace_root(), prompt_dir, user_prompt_file)
    user_interpolated, unmapped = interpolate_prompt(user_content, get_workspace_root(), workspace_vars)

    if unmapped:
        error_msg = f"❌ Unmapped variables: {', '.join(unmapped)}"
        return error_msg, {}, {}, error_msg

    messages.append({"role": "user", "content": user_interpolated})

    # Call LLM
    formatted_response, raw_request, raw_response = call_llm_api(
        api_key,
        base_url or None,
        model,
        messages,
        temperature,
        max_tokens,
    )

    # Calculate stats
    usage = raw_response.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    cost = estimate_cost(model, prompt_tokens, completion_tokens)

    # Build status
    if "error" in raw_response:
        status = f"❌ Error: {raw_response['error']}"
    else:
        status = f"✅ Success | Tokens: {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens}) | Cost: ~{cost}"

    return formatted_response, raw_request, raw_response, status


# ============================================================================
# Main UI
# ============================================================================


def create_ui():
    """Create Gradio UI."""
    # Check if user config exists
    user_config = load_user_config()
    user_config_valid = not validate_user_config(user_config)

    with gr.Blocks(title="Prompt Engineer") as demo:
        gr.Markdown(f"# 🎯 Prompt Engineer\nWorkspace: `{get_workspace_root()}`")
        gr.Markdown("CLI-based prompt engineering workbench for rapid iteration")

        # ====================================================================
        # Section 1: User Config
        # ====================================================================

        with gr.Accordion("⚙️ User Configuration", open=not user_config_valid) as user_config_section:
            gr.Markdown("### Provider Settings (saved to `~/.prompt-engineer/config.yaml`)")

            with gr.Row():
                provider_dropdown = gr.Dropdown(
                    choices=["openai", "ollama", "lm-studio", "openrouter"],
                    value=user_config.get("provider", "openai"),
                    label="Provider Preset",
                )

            with gr.Row():
                api_key_input = gr.Textbox(
                    label="API Key",
                    value=user_config.get("api_key", ""),
                    type="password",
                    placeholder="Enter API key (or 'not-needed' for local models)",
                )

            with gr.Row():
                base_url_input = gr.Textbox(
                    label="Base URL",
                    value=user_config.get("base_url", ""),
                    placeholder="Leave empty for OpenAI, or enter custom endpoint",
                )

            gr.Markdown("### Available Models")

            with gr.Row():
                load_models_btn = gr.Button("🔄 Load Models from Provider", size="sm")
                models_status = gr.Textbox(label="Status", value="", interactive=False, show_label=False)

            with gr.Row():
                models_multiselect = gr.Dropdown(
                    choices=user_config.get("models", []),
                    value=user_config.get("models", []),
                    label="Select Models",
                    multiselect=True,
                    allow_custom_value=True,
                )

            gr.Markdown("### Default Settings")

            with gr.Row():
                default_model_dropdown = gr.Dropdown(
                    choices=user_config.get("models", []),
                    value=user_config.get("defaults", {}).get("model", "gpt-4o"),
                    label="Default Model",
                    allow_custom_value=True,
                )

            with gr.Row():
                default_temperature = gr.Slider(
                    minimum=0,
                    maximum=2,
                    value=user_config.get("defaults", {}).get("temperature", 0.7),
                    step=0.1,
                    label="Temperature",
                )
                default_max_tokens = gr.Slider(
                    minimum=1,
                    maximum=4000,
                    value=user_config.get("defaults", {}).get("max_tokens", 2000),
                    step=100,
                    label="Max Tokens",
                )

            save_user_config_btn = gr.Button("💾 Save User Config", variant="primary")
            user_config_status = gr.Textbox(label="Status", lines=2)

        # ====================================================================
        # Section 2: Workspace Config
        # ====================================================================

        with gr.Accordion("📁 Workspace Configuration", open=True) as workspace_config_section:
            gr.Markdown(f"### Workspace Settings (saved to `{get_workspace_root()}/.prompt-engineer/workspace.yaml`)")

            workspace_name, workspace_prompt_dir, workspace_data_dir, workspace_var_rows, workspace_status_initial = load_workspace_config_ui()

            with gr.Row():
                workspace_name_input = gr.Textbox(
                    label="Workspace Name",
                    value=workspace_name,
                    placeholder="My Workspace",
                )

            with gr.Row():
                prompt_dir_input = gr.Textbox(
                    label="Prompts Directory",
                    value=workspace_prompt_dir,
                    placeholder="prompts",
                )
                data_dir_input = gr.Textbox(
                    label="Data Directory",
                    value=workspace_data_dir,
                    placeholder="prompt-data",
                )

            save_workspace_config_btn = gr.Button("💾 Save Workspace Config", size="sm")

            gr.Markdown("### Variable Mappings")

            with gr.Row():
                var_name_input = gr.Textbox(label="Variable Name", scale=2, placeholder="my_variable")
                var_type_radio = gr.Radio(["file", "value"], label="Type", value="value", scale=1)

            var_source_input = gr.Textbox(
                label="File Path (relative to workspace) or Value",
                lines=3,
                placeholder="prompt-data/my-file.txt or inline text value",
            )

            add_var_btn = gr.Button("➕ Add Variable", size="sm")

            var_table = gr.Dataframe(
                headers=["Name", "Type", "Source"],
                value=workspace_var_rows,
                label="Defined Variables",
                interactive=False,
            )

            with gr.Row():
                refresh_workspace_btn = gr.Button("🔄 Refresh from Disk", size="sm")
                workspace_config_status = gr.Textbox(
                    label="Status",
                    value=workspace_status_initial,
                    interactive=False,
                    lines=3,
                )

        # ====================================================================
        # Section 3: Prompt Editor
        # ====================================================================

        with gr.Accordion("✏️ Prompt Editor", open=True) as prompt_editor_section:
            gr.Markdown("### Edit Prompt Files")

            with gr.Row():
                prompt_file_dropdown = gr.Dropdown(
                    choices=get_available_prompts(),
                    label="Select Prompt File",
                    scale=3,
                )
                refresh_prompts_btn = gr.Button("🔄 Refresh", size="sm", scale=1)
                save_prompt_btn = gr.Button("💾 Save", size="sm", scale=1)

            with gr.Tabs():
                with gr.Tab("Editor"):
                    prompt_editor = gr.Textbox(
                        label="Prompt Template (use {variable_name} syntax)",
                        lines=15,
                        placeholder="Enter your prompt template...\n\nExample:\nYou are a helpful assistant.\n\nUser question: {question}",
                    )

                with gr.Tab("Interpolated Preview"):
                    prompt_preview = gr.Textbox(
                        label="Interpolated Prompt (read-only preview)",
                        lines=15,
                        interactive=False,
                    )

            prompt_status = gr.Textbox(label="Status", interactive=False)

        # ====================================================================
        # Section 4: LLM Interaction
        # ====================================================================

        with gr.Accordion("🚀 LLM Interaction", open=True) as llm_section:
            gr.Markdown("### Execute Prompts")

            with gr.Row():
                system_prompt_dropdown = gr.Dropdown(
                    choices=get_available_prompts(),
                    value="(none)",
                    label="System Prompt",
                    scale=1,
                )
                user_prompt_dropdown = gr.Dropdown(
                    choices=get_available_prompts(),
                    label="User Prompt (required)",
                    scale=1,
                )

            with gr.Row():
                model_override_dropdown = gr.Dropdown(
                    choices=user_config.get("models", []),
                    label="Model Override (leave empty to use default)",
                    allow_custom_value=True,
                )

            with gr.Row():
                temperature_slider = gr.Slider(
                    minimum=0,
                    maximum=2,
                    value=user_config.get("defaults", {}).get("temperature", 0.7),
                    step=0.1,
                    label="Temperature",
                )
                max_tokens_slider = gr.Slider(
                    minimum=1,
                    maximum=4000,
                    value=user_config.get("defaults", {}).get("max_tokens", 2000),
                    step=100,
                    label="Max Tokens",
                )

            run_prompt_btn = gr.Button("🚀 Run Prompt", variant="primary", size="lg")

            with gr.Tabs():
                with gr.Tab("Formatted Response"):
                    formatted_response_md = gr.Markdown(label="Formatted Response", value="")

                with gr.Tab("Raw Request"):
                    raw_request_json = gr.JSON(label="Raw Request Payload", value={})

                with gr.Tab("Raw Response"):
                    raw_response_json = gr.JSON(label="Raw API Response", value={})

            llm_status = gr.Textbox(label="Status", interactive=False)

        # ====================================================================
        # Event Handlers
        # ====================================================================

        # Section 1: User Config
        provider_dropdown.change(
            fn=update_provider_preset,
            inputs=[provider_dropdown],
            outputs=[base_url_input, models_multiselect, default_model_dropdown, models_status],
        )

        load_models_btn.click(
            fn=load_models_from_provider,
            inputs=[api_key_input, base_url_input],
            outputs=[models_multiselect, models_status, default_model_dropdown],
        )

        save_user_config_btn.click(
            fn=save_user_config_ui,
            inputs=[
                provider_dropdown,
                api_key_input,
                base_url_input,
                models_multiselect,
                default_model_dropdown,
                default_temperature,
                default_max_tokens,
            ],
            outputs=[user_config_status],
        )

        # Section 2: Workspace Config
        save_workspace_config_btn.click(
            fn=save_workspace_config_ui,
            inputs=[workspace_name_input, prompt_dir_input, data_dir_input],
            outputs=[workspace_config_status],
        )

        add_var_btn.click(
            fn=add_variable_ui,
            inputs=[var_name_input, var_type_radio, var_source_input],
            outputs=[var_table, workspace_config_status],
        )

        refresh_workspace_btn.click(
            fn=refresh_workspace_config,
            outputs=[
                workspace_name_input,
                prompt_dir_input,
                data_dir_input,
                var_table,
                workspace_config_status,
            ],
        )

        # Section 3: Prompt Editor
        refresh_prompts_btn.click(
            fn=refresh_prompt_list,
            outputs=[prompt_file_dropdown, prompt_status],
        )

        prompt_file_dropdown.change(
            fn=load_prompt_ui,
            inputs=[prompt_file_dropdown],
            outputs=[prompt_editor, prompt_preview, prompt_status],
        )

        prompt_editor.change(
            fn=update_interpolated_preview,
            inputs=[prompt_editor],
            outputs=[prompt_preview],
        )

        prompt_editor.change(
            fn=validate_prompt_variables_ui,
            inputs=[prompt_editor],
            outputs=[prompt_status],
        )

        save_prompt_btn.click(
            fn=save_prompt_ui,
            inputs=[prompt_file_dropdown, prompt_editor],
            outputs=[prompt_status],
        )

        # Section 4: LLM Interaction
        run_prompt_btn.click(
            fn=run_prompt_ui,
            inputs=[
                system_prompt_dropdown,
                user_prompt_dropdown,
                model_override_dropdown,
                temperature_slider,
                max_tokens_slider,
            ],
            outputs=[formatted_response_md, raw_request_json, raw_response_json, llm_status],
        )

    return demo


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Prompt Engineer - CLI-based prompt engineering workbench")
    parser.add_argument(
        "--workspace",
        type=str,
        default=os.getcwd(),
        help="Workspace root directory (default: current directory)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run Gradio server (default: 7860)",
    )

    args = parser.parse_args()

    # Set workspace root
    set_workspace_root(args.workspace)

    print(f"🎯 Prompt Engineer")
    print(f"Workspace: {get_workspace_root()}")
    print(f"Starting server on port {args.port}...")

    # Create and launch UI
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
