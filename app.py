import gradio as gr
import os
from openai import OpenAI
from dotenv import load_dotenv, set_key, find_dotenv
import json
import re

# Load environment variables
load_dotenv()

# Provider presets for easy configuration
PROVIDER_PRESETS = {
    "OpenAI": {
        "base_url": "",
        "api_key_required": True,
        "default_models": "gpt-4o,gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo",
        "api_key_placeholder": "sk-..."
    },
    "Ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_required": False,
        "default_models": "llama3.2,mistral,codellama,phi3",
        "api_key_placeholder": "not-needed"
    },
    "LM Studio": {
        "base_url": "http://localhost:1234/v1",
        "api_key_required": False,
        "default_models": "",
        "api_key_placeholder": "not-needed"
    },
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_required": True,
        "default_models": "anthropic/claude-3.5-sonnet,openai/gpt-4o,meta-llama/llama-3.2-90b",
        "api_key_placeholder": "sk-or-v1-..."
    },
    "vLLM": {
        "base_url": "http://localhost:8000/v1",
        "api_key_required": False,
        "default_models": "",
        "api_key_placeholder": "not-needed"
    },
    "Custom": {
        "base_url": "",
        "api_key_required": True,
        "default_models": "",
        "api_key_placeholder": "your-api-key"
    }
}

# Global configuration state
config_state = {
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "base_url": os.getenv("OPENAI_BASE_URL", ""),
    "provider_name": os.getenv("PROVIDER_NAME", "OpenAI"),
    "models": os.getenv("AVAILABLE_MODELS", ""),
    "default_model": os.getenv("DEFAULT_MODEL", ""),
    "temperature": float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("DEFAULT_MAX_TOKENS", "1000"))
}

# Check if configuration is needed (first run)
def needs_configuration():
    """Check if the app needs initial configuration."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    # Consider configured if API key is set or base URL is set (for local models)
    return not api_key and not os.getenv("OPENAI_BASE_URL")

def save_config_to_env(api_key, base_url, provider_name, models, default_model, temperature, max_tokens):
    """Save configuration to .env file."""
    env_file = find_dotenv()
    if not env_file:
        env_file = ".env"
        # Create .env if it doesn't exist
        with open(env_file, "w") as f:
            f.write("")

    # Update .env file
    set_key(env_file, "OPENAI_API_KEY", api_key or "not-needed")
    set_key(env_file, "OPENAI_BASE_URL", base_url or "")
    set_key(env_file, "PROVIDER_NAME", provider_name or "OpenAI")
    set_key(env_file, "AVAILABLE_MODELS", models or "")
    set_key(env_file, "DEFAULT_MODEL", default_model or "")
    set_key(env_file, "DEFAULT_TEMPERATURE", str(temperature))
    set_key(env_file, "DEFAULT_MAX_TOKENS", str(max_tokens))

    # Update global config state
    config_state["api_key"] = api_key or "not-needed"
    config_state["base_url"] = base_url or ""
    config_state["provider_name"] = provider_name or "OpenAI"
    config_state["models"] = models or ""
    config_state["default_model"] = default_model or ""
    config_state["temperature"] = temperature
    config_state["max_tokens"] = max_tokens

    return "✅ Configuration saved! Restart the app for changes to take full effect."

def get_provider_preset(provider_name):
    """Get preset configuration for a provider."""
    preset = PROVIDER_PRESETS.get(provider_name, PROVIDER_PRESETS["Custom"])
    return (
        preset["base_url"],
        preset["default_models"],
        preset["api_key_placeholder"]
    )

def fetch_available_models(api_key, base_url):
    """
    Fetch available models from the provider's API.
    Returns (success: bool, result: list or error message).
    """
    try:
        # Create temporary client with provided credentials
        temp_client = OpenAI(api_key=api_key or "not-needed", base_url=base_url or None)

        # Fetch models from the API
        models_response = temp_client.models.list()

        # Extract model IDs
        model_ids = [model.id for model in models_response.data]

        if not model_ids:
            return False, "No models found at the specified endpoint"

        # Sort models alphabetically
        model_ids.sort()

        return True, model_ids

    except Exception as e:
        error_msg = str(e)
        if "Connection" in error_msg or "connect" in error_msg.lower():
            return False, f"Connection failed: Unable to reach {base_url or 'OpenAI API'}. Check the URL and network."
        elif "401" in error_msg or "Unauthorized" in error_msg:
            return False, "Authentication failed: Invalid API key"
        elif "403" in error_msg or "Forbidden" in error_msg:
            return False, "Access forbidden: Check your API key permissions"
        else:
            return False, f"Error fetching models: {error_msg}"

def initialize_client():
    """Initialize the OpenAI client with current configuration."""
    api_key = config_state["api_key"] or "not-needed"
    base_url = config_state["base_url"] or None

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    else:
        return OpenAI(api_key=api_key)

# Initialize client
client = initialize_client()

# Get available models
def get_models_list():
    """Get list of available models from configuration."""
    models_str = config_state["models"]
    if models_str:
        return [model.strip() for model in models_str.split(",")]
    else:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

MODELS = get_models_list()

def extract_variables(template: str) -> list:
    """Extract variable names from a prompt template."""
    return sorted(list(set(re.findall(r'\{(\w+)\}', template))))

def load_file_content(filepath: str) -> str:
    """Load content from a file."""
    try:
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"

        with open(filepath, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def parse_variable_config(config_text: str) -> dict:
    """
    Parse variable configuration from text format.
    Format:
        variable_name: file:path/to/file.md
        or
        variable_name: value:Some fixed text
    """
    config = {}
    lines = config_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if ':' not in line:
            continue

        parts = line.split(':', 2)
        if len(parts) < 3:
            continue

        var_name = parts[0].strip()
        var_type = parts[1].strip()
        content = parts[2].strip()

        if var_type in ['file', 'value']:
            config[var_name] = {"type": var_type, "content": content}

    return config

def generate_variable_config_template(template: str) -> str:
    """Generate a config template from prompt variables."""
    variables = extract_variables(template)

    if not variables:
        return "# No variables found in template"

    lines = ["# Variable Configuration"]
    lines.append("# Format: variable_name:type:content")
    lines.append("# Types: 'file' (path to file) or 'value' (fixed text)")
    lines.append("")

    for var in variables:
        lines.append(f"{var}:value:")

    return '\n'.join(lines)

def build_variables_dict(var_config_text: str) -> dict:
    """Build variables dictionary from config text."""
    config = parse_variable_config(var_config_text)
    result = {}

    for var_name, settings in config.items():
        if settings["type"] == "file":
            result[var_name] = load_file_content(settings["content"])
        else:
            result[var_name] = settings["content"]

    return result

def format_prompt(template: str, var_config_text: str) -> str:
    """Format the prompt template with variables."""
    try:
        vars_dict = build_variables_dict(var_config_text)
        return template.format(**vars_dict)
    except KeyError as e:
        return f"Error: Missing variable {e} in configuration"
    except Exception as e:
        return f"Error formatting prompt: {e}"

def call_llm_api(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    """Call OpenAI-compatible API with the given prompt and parameters."""
    try:
        # Reinitialize client in case config changed
        current_client = initialize_client()
        response = current_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling {config_state['provider_name']} API: {e}"

def call_llm_api_full(prompt: str, model: str, temperature: float, max_tokens: int) -> tuple:
    """
    Call OpenAI-compatible API and return both formatted content and raw response.
    Returns: (formatted_content: str, raw_response: dict)
    """
    try:
        # Reinitialize client in case config changed
        current_client = initialize_client()
        response = current_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Extract formatted content
        formatted_content = response.choices[0].message.content

        # Convert response to dict for raw view
        raw_response = response.model_dump()

        return formatted_content, raw_response
    except Exception as e:
        error_msg = f"Error calling {config_state['provider_name']} API: {e}"
        return error_msg, {"error": str(e)}

def test_prompt_handler(template: str, var_config: str, model: str, temperature: float, max_tokens: int):
    """Test the prompt with variable configurations."""
    formatted_prompt = format_prompt(template, var_config)

    if formatted_prompt.startswith("Error"):
        return formatted_prompt, formatted_prompt, ""

    response = call_llm_api(formatted_prompt, model, temperature, max_tokens)
    return formatted_prompt, response, ""

def save_template(template: str, var_config: str, name: str):
    """Save template and variable configuration."""
    if not name:
        return "Please provide a template name"

    os.makedirs("templates", exist_ok=True)
    template_path = f"templates/{name}.txt"
    config_path = f"templates/{name}.vars"

    with open(template_path, "w") as f:
        f.write(template)

    with open(config_path, "w") as f:
        f.write(var_config)

    return f"Saved: {template_path} and {config_path}"

def load_template(name: str):
    """Load template and variable configuration."""
    if not name:
        return "", "", "Please provide a template name"

    template_path = f"templates/{name}.txt"
    config_path = f"templates/{name}.vars"

    if not os.path.exists(template_path):
        return "", "", f"Template {template_path} not found"

    with open(template_path, "r") as f:
        template = f.read()

    var_config = ""
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            var_config = f.read()
    else:
        var_config = generate_variable_config_template(template)

    return template, var_config, f"Loaded: {name}"

def list_templates():
    """List all saved templates."""
    if not os.path.exists("templates"):
        return "No templates directory found"

    templates = [f.replace(".txt", "") for f in os.listdir("templates") if f.endswith(".txt")]
    if not templates:
        return "No templates found"

    return "Available templates:\n" + "\n".join(f"  - {t}" for t in templates)

# Create Gradio interface
with gr.Blocks(title="Prompt Engineer") as demo:

    # Header with settings button
    with gr.Row():
        gr.Markdown(f"# 🎯 Prompt Engineer ({config_state['provider_name']})")
        settings_btn = gr.Button("⚙️ Settings", size="sm", scale=0)

    gr.Markdown("Iterate on AI prompts with file-based or fixed variables - no restart needed!")

    # Configuration Panel (collapsible)
    with gr.Accordion("⚙️ Configuration", open=needs_configuration()) as config_accordion:
        gr.Markdown("### Provider Configuration")

        with gr.Row():
            provider_dropdown = gr.Dropdown(
                choices=list(PROVIDER_PRESETS.keys()),
                value=config_state["provider_name"],
                label="Provider",
                info="Select a preset or choose 'Custom'"
            )

        with gr.Row():
            base_url_input = gr.Textbox(
                label="Base URL",
                value=config_state["base_url"],
                placeholder="Leave empty for OpenAI, or enter custom endpoint",
                info="e.g., http://localhost:11434/v1 for Ollama"
            )

        with gr.Row():
            api_key_input = gr.Textbox(
                label="API Key",
                value=config_state["api_key"],
                placeholder="your-api-key",
                type="password",
                info="Enter 'not-needed' for local models"
            )

        gr.Markdown("### Available Models")

        with gr.Row():
            load_models_btn = gr.Button("🔄 Load Models from Provider", size="sm")
            models_status = gr.Textbox(
                label="Status",
                value="",
                scale=2,
                interactive=False,
                show_label=False
            )

        with gr.Row():
            # Initialize with current models from config
            current_models = [m.strip() for m in config_state["models"].split(",") if m.strip()]
            selected_models = gr.Dropdown(
                choices=current_models,
                value=current_models,
                label="Select Models to Use",
                multiselect=True,
                allow_custom_value=True,
                info="Load models from provider or enter custom model names"
            )

        gr.Markdown("### Model Settings (Defaults)")

        with gr.Row():
            # Use saved default_model from config, or fallback to first available model
            default_model_value = config_state["default_model"] or (MODELS[0] if MODELS else "")
            config_model_dropdown = gr.Dropdown(
                choices=MODELS,
                value=default_model_value,
                label="Default Model",
                allow_custom_value=True,
                info="Select which model to use by default for testing prompts"
            )

        with gr.Row():
            config_temperature_slider = gr.Slider(
                minimum=0,
                maximum=2,
                value=config_state["temperature"],
                step=0.1,
                label="Temperature"
            )

            config_max_tokens_slider = gr.Slider(
                minimum=1,
                maximum=4000,
                value=config_state["max_tokens"],
                step=100,
                label="Max Tokens"
            )

        save_config_btn = gr.Button("💾 Save Configuration", variant="primary")
        config_status = gr.Textbox(label="Configuration Status", lines=2)

    # Main UI
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Prompt Template")
            template_input = gr.Textbox(
                label="Prompt Template",
                placeholder="Enter your prompt template here. Use {variable_name} for variables.",
                lines=12,
                value="You are a helpful assistant.\n\nUser question: {question}"
            )

            parse_vars_btn = gr.Button("🔍 Generate Variable Config", size="sm")

            gr.Markdown("### 2. Variable Configuration")
            gr.Markdown(
                "**Format:** `variable_name:type:content`\n\n"
                "- **file**: `variable_name:file:path/to/file.md`\n"
                "- **value**: `variable_name:value:Your fixed text here`"
            )

            var_config_input = gr.Textbox(
                label="Variable Configuration",
                placeholder="question:value:What is the capital of France?",
                lines=8,
                value="question:value:What is the capital of France?"
            )

            with gr.Row():
                preview_button = gr.Button("🔍 Preview Prompt", size="lg")
                test_button = gr.Button("🚀 Test Prompt", variant="primary", size="lg")

            gr.Markdown("### 3. Template Management")
            with gr.Row():
                template_name_input = gr.Textbox(
                    label="Template Name",
                    placeholder="my_template",
                    scale=3
                )
                save_button = gr.Button("💾 Save", scale=1)
                load_button = gr.Button("📂 Load", scale=1)
                list_button = gr.Button("📋 List", scale=1)

            save_status = gr.Textbox(label="Status", lines=3)

        with gr.Column(scale=1):
            gr.Markdown("### Model Selection")
            # Session model selector - initialized with default model from config
            session_model_value = config_state["default_model"] or (MODELS[0] if MODELS else "gpt-4o")
            session_model_dropdown = gr.Dropdown(
                choices=MODELS,
                value=session_model_value,
                label="Model (Session)",
                allow_custom_value=True,
                info="Select model for this session (does not change config default)"
            )

            gr.Markdown("### Formatted Prompt")
            formatted_output = gr.Textbox(
                label="This is what gets sent to the API",
                lines=10,
                interactive=False
            )

            gr.Markdown("### API Response")

            with gr.Row():
                view_mode = gr.Radio(
                    choices=["Formatted", "Raw"],
                    value="Formatted",
                    label="View Mode",
                    info="Toggle between formatted output and raw API response"
                )

            # Formatted view - renders markdown/JSON/YAML
            response_formatted = gr.Markdown(
                label="Formatted Response",
                value="",
                visible=True
            )

            # Raw view - shows full API response as JSON
            response_raw = gr.JSON(
                label="Raw API Response",
                value=None,
                visible=False
            )

    # Configuration event handlers
    def update_config_from_preset(provider_name):
        """Update configuration inputs when provider preset is selected."""
        base_url, models, api_key_placeholder = get_provider_preset(provider_name)
        # Convert default models to list for multi-select dropdown
        models_list = [m.strip() for m in models.split(",") if m.strip()] if models else []
        default_model = models_list[0] if models_list else None
        return (
            base_url,
            gr.update(choices=models_list, value=models_list),
            api_key_placeholder,
            "",
            gr.update(choices=models_list, value=default_model),
            gr.update(choices=models_list, value=default_model)
        )

    def load_models_from_provider(api_key, base_url):
        """Load available models from the provider's API."""
        if not base_url and not api_key:
            return (
                gr.update(choices=[]),
                "⚠️ Please configure Base URL and API Key first",
                gr.update(choices=[]),
                gr.update(choices=[])
            )

        success, result = fetch_available_models(api_key, base_url)

        if success:
            default_model = result[0] if result else None
            return (
                gr.update(choices=result, value=result),
                f"✅ Loaded {len(result)} models successfully",
                gr.update(choices=result, value=default_model),
                gr.update(choices=result, value=default_model)
            )
        else:
            return (
                gr.update(choices=[]),
                f"❌ {result}",
                gr.update(choices=[]),
                gr.update(choices=[])
            )

    def save_config_with_models(api_key, base_url, provider_name, selected_models_list,
                               default_model, temperature, max_tokens):
        """Save configuration with selected models."""
        # Convert list to comma-separated string
        models_str = ",".join(selected_models_list) if selected_models_list else ""
        return save_config_to_env(api_key, base_url, provider_name, models_str,
                                 default_model, temperature, max_tokens)

    def update_default_model_choices(selected_models_list):
        """Update the default model dropdown when selected models change."""
        if not selected_models_list:
            return gr.update(choices=[])
        return gr.update(
            choices=selected_models_list,
            value=selected_models_list[0] if selected_models_list else None
        )

    provider_dropdown.change(
        fn=update_config_from_preset,
        inputs=[provider_dropdown],
        outputs=[base_url_input, selected_models, api_key_input, models_status, config_model_dropdown, session_model_dropdown]
    )

    load_models_btn.click(
        fn=load_models_from_provider,
        inputs=[api_key_input, base_url_input],
        outputs=[selected_models, models_status, config_model_dropdown, session_model_dropdown]
    )

    selected_models.change(
        fn=update_default_model_choices,
        inputs=[selected_models],
        outputs=[config_model_dropdown]
    )

    save_config_btn.click(
        fn=save_config_with_models,
        inputs=[api_key_input, base_url_input, provider_dropdown, selected_models,
                config_model_dropdown, config_temperature_slider, config_max_tokens_slider],
        outputs=[config_status]
    )

    settings_btn.click(
        fn=lambda: gr.Accordion(open=True),
        outputs=[config_accordion]
    )

    # Main UI event handlers
    parse_vars_btn.click(
        fn=generate_variable_config_template,
        inputs=[template_input],
        outputs=[var_config_input]
    )

    def preview_prompt(template, var_config):
        """Preview the formatted prompt without calling the API."""
        formatted = format_prompt(template, var_config)
        return formatted, "", None, ""

    def format_and_prepare(template, var_config):
        """Format the prompt and show it immediately before API call."""
        formatted = format_prompt(template, var_config)
        if formatted.startswith("Error"):
            return formatted, formatted, None, ""
        return formatted, "⏳ Calling API...", None, ""

    def call_api_async(template, var_config, model):
        """Make the API call and return both formatted and raw responses."""
        # Format the prompt again (needed for API call)
        formatted = format_prompt(template, var_config)

        if formatted.startswith("Error"):
            return formatted, {"error": "Prompt formatting failed"}

        # Call the API with the selected session model
        formatted_response, raw_response = call_llm_api_full(
            formatted,
            model,
            config_state["temperature"],
            config_state["max_tokens"]
        )
        return formatted_response, raw_response

    def toggle_view(mode):
        """Toggle between formatted and raw response views."""
        if mode == "Formatted":
            return gr.update(visible=True), gr.update(visible=False)
        else:  # Raw
            return gr.update(visible=False), gr.update(visible=True)

    view_mode.change(
        fn=toggle_view,
        inputs=[view_mode],
        outputs=[response_formatted, response_raw]
    )

    preview_button.click(
        fn=preview_prompt,
        inputs=[template_input, var_config_input],
        outputs=[formatted_output, response_formatted, response_raw, save_status]
    )

    # Chain the test prompt: first format (immediate), then call API (async)
    test_button.click(
        fn=format_and_prepare,
        inputs=[template_input, var_config_input],
        outputs=[formatted_output, response_formatted, response_raw, save_status]
    ).then(
        fn=call_api_async,
        inputs=[template_input, var_config_input, session_model_dropdown],
        outputs=[response_formatted, response_raw]
    )

    save_button.click(
        fn=save_template,
        inputs=[template_input, var_config_input, template_name_input],
        outputs=[save_status]
    )

    load_button.click(
        fn=load_template,
        inputs=[template_name_input],
        outputs=[template_input, var_config_input, save_status]
    )

    list_button.click(
        fn=list_templates,
        outputs=[save_status]
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        theme=gr.themes.Soft(),
        css="""
        .config-header { display: flex; align-items: center; justify-content: space-between; }
    """)
