import gradio as gr
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()

# Initialize OpenAI-compatible client with configurable base URL
api_key = os.getenv("OPENAI_API_KEY", "not-needed")  # Some local models don't need a key
base_url = os.getenv("OPENAI_BASE_URL", None)  # e.g., "http://localhost:11434/v1" for Ollama

# Initialize client with optional base_url
if base_url:
    client = OpenAI(api_key=api_key, base_url=base_url)
else:
    client = OpenAI(api_key=api_key)

# Get available models from environment or use defaults
default_models = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]

# Load models from environment variable (comma-separated list)
models_env = os.getenv("AVAILABLE_MODELS", None)
if models_env:
    MODELS = [model.strip() for model in models_env.split(",")]
else:
    MODELS = default_models

# Get provider name for display
PROVIDER_NAME = os.getenv("PROVIDER_NAME", "OpenAI")

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
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling {PROVIDER_NAME} API: {e}"

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
with gr.Blocks(title="Prompt Engineer", theme=gr.themes.Soft()) as demo:
    gr.Markdown(f"# 🎯 Prompt Engineer ({PROVIDER_NAME})")
    gr.Markdown("Iterate on AI prompts with file-based or fixed variables - no restart needed!")

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

            gr.Markdown("### 3. Model Settings")
            with gr.Row():
                model_dropdown = gr.Dropdown(
                    choices=MODELS,
                    value=MODELS[0] if MODELS else "",
                    label="Model",
                    allow_custom_value=True
                )

            with gr.Row():
                temperature_slider = gr.Slider(
                    minimum=0,
                    maximum=2,
                    value=0.7,
                    step=0.1,
                    label="Temperature"
                )

                max_tokens_slider = gr.Slider(
                    minimum=1,
                    maximum=4000,
                    value=1000,
                    step=100,
                    label="Max Tokens"
                )

            test_button = gr.Button("🚀 Test Prompt", variant="primary", size="lg")

            gr.Markdown("### 4. Template Management")
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
            gr.Markdown("### Formatted Prompt")
            formatted_output = gr.Textbox(
                label="This is what gets sent to the API",
                lines=10,
                interactive=False
            )

            gr.Markdown("### API Response")
            response_output = gr.Textbox(
                label="Model Output",
                lines=18,
                interactive=False
            )

    # Event handlers
    parse_vars_btn.click(
        fn=generate_variable_config_template,
        inputs=[template_input],
        outputs=[var_config_input]
    )

    test_button.click(
        fn=test_prompt_handler,
        inputs=[template_input, var_config_input, model_dropdown, temperature_slider, max_tokens_slider],
        outputs=[formatted_output, response_output, save_status]
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
    demo.launch(server_name="0.0.0.0", server_port=7860)
