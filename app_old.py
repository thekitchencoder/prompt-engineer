import gradio as gr
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import re
import yaml

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Available models
MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]

# Global state for variable configurations
variable_configs = {}

def extract_variables(template: str) -> list:
    """
    Extract variable names from a prompt template.
    Finds all {variable_name} patterns.
    """
    return list(set(re.findall(r'\{(\w+)\}', template)))

def load_file_content(filepath: str) -> str:
    """
    Load content from a file. Supports text, markdown, YAML, etc.
    """
    try:
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"

        with open(filepath, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def build_variables_dict(var_configs: dict) -> dict:
    """
    Build a dictionary of variable values based on configurations.
    var_configs format: {var_name: {"type": "file"|"value", "content": "..."}}
    """
    result = {}

    for var_name, config in var_configs.items():
        if config["type"] == "file":
            # Load from file
            content = load_file_content(config["content"])
            result[var_name] = content
        else:
            # Use fixed value
            result[var_name] = config["content"]

    return result

def format_prompt(template: str, var_configs: dict) -> str:
    """
    Format the prompt template with variables from configurations.
    """
    try:
        vars_dict = build_variables_dict(var_configs)
        return template.format(**vars_dict)
    except KeyError as e:
        return f"Error: Missing variable {e} in template"
    except Exception as e:
        return f"Error formatting prompt: {e}"

def call_openai(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    """
    Call OpenAI API with the given prompt and parameters.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling OpenAI API: {e}"

def save_template(template: str, name: str, var_configs: dict):
    """
    Save a prompt template and its variable configuration to files.
    """
    if not name:
        return "Please provide a template name"

    os.makedirs("templates", exist_ok=True)
    template_path = f"templates/{name}.txt"
    config_path = f"templates/{name}.config.json"

    # Save template
    with open(template_path, "w") as f:
        f.write(template)

    # Save variable configuration
    with open(config_path, "w") as f:
        json.dump(var_configs, f, indent=2)

    return f"Template and config saved to {template_path}"

def load_template(name: str):
    """
    Load a prompt template and its variable configuration from files.
    Returns: (template_text, var_configs_dict, status_message)
    """
    if not name:
        return "", {}, "Please provide a template name"

    template_path = f"templates/{name}.txt"
    config_path = f"templates/{name}.config.json"

    if not os.path.exists(template_path):
        return "", {}, f"Template {template_path} not found"

    # Load template
    with open(template_path, "r") as f:
        template = f.read()

    # Load configuration if exists
    var_configs = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            var_configs = json.load(f)

    return template, var_configs, f"Loaded {name}"

def list_templates():
    """
    List all saved templates.
    """
    if not os.path.exists("templates"):
        return "No templates directory found"

    templates = [f.replace(".txt", "") for f in os.listdir("templates") if f.endswith(".txt")]
    if not templates:
        return "No templates found"

    return "\n".join(templates)

# Create Gradio interface with custom CSS for better styling
css = """
.variable-section {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    background-color: #f9f9f9;
}
"""

def create_variable_ui():
    """Create the UI components for variable configuration."""
    with gr.Accordion("📝 Variables Configuration", open=True):
        variables_state = gr.State({})
        variables_display = gr.JSON(label="Current Variables", value={})

        gr.Markdown("Variables will appear here after you update the template.")

        # Dynamic variable inputs container
        var_inputs_column = gr.Column(visible=False)

    return variables_state, variables_display, var_inputs_column

def update_variables_from_template(template: str, current_vars: dict):
    """
    Update variables configuration when template changes.
    Preserves existing configurations where possible.
    """
    detected_vars = extract_variables(template)

    # Initialize new vars with defaults, preserve existing configs
    new_vars = {}
    for var in detected_vars:
        if var in current_vars:
            new_vars[var] = current_vars[var]
        else:
            # Default to fixed value with empty content
            new_vars[var] = {"type": "value", "content": ""}

    return new_vars, new_vars

def update_var_config(var_name: str, var_type: str, content: str, current_vars: dict):
    """Update a single variable's configuration."""
    current_vars[var_name] = {"type": var_type, "content": content}
    return current_vars, current_vars

def test_prompt_with_vars(template: str, var_configs: dict, model: str, temperature: float, max_tokens: int):
    """Test the prompt with variable configurations."""
    # Format the prompt
    formatted_prompt = format_prompt(template, var_configs)

    # If there was an error formatting, return it
    if formatted_prompt.startswith("Error"):
        return formatted_prompt, formatted_prompt, ""

    # Call OpenAI
    response = call_openai(formatted_prompt, model, temperature, max_tokens)

    return formatted_prompt, response, ""

# Main Gradio interface
with gr.Blocks(title="Prompt Engineer", css=css) as demo:
    gr.Markdown("# 🎯 Prompt Engineer")
    gr.Markdown("Iterate on your AI prompts quickly without restarting the app!")

    # State for variable configurations
    var_configs_state = gr.State({})

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Prompt Template")
            template_input = gr.Textbox(
                label="Prompt Template",
                placeholder="Enter your prompt template here. Use {variable_name} for variables.",
                lines=10,
                value="You are a helpful assistant.\n\nUser question: {question}"
            )

            parse_button = gr.Button("🔍 Parse Variables", size="sm")

            gr.Markdown("### Variables")
            gr.Markdown("Configure each variable to use either a fixed value or load from a file.")

            # Container for dynamic variable inputs
            variables_container = gr.Column()

            with variables_container:
                detected_vars_display = gr.JSON(
                    label="Detected Variables",
                    value={},
                    visible=False
                )

                # We'll dynamically create variable inputs
                var_inputs = {}

            gr.Markdown("### Model Settings")
            with gr.Row():
                model_dropdown = gr.Dropdown(
                    choices=MODELS,
                    value=MODELS[0],
                    label="Model"
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

            test_button = gr.Button("🚀 Test Prompt", variant="primary")

            gr.Markdown("### Template Management")
            with gr.Row():
                template_name_input = gr.Textbox(
                    label="Template Name",
                    placeholder="my_template"
                )
                save_button = gr.Button("💾 Save")
                load_button = gr.Button("📂 Load")
                list_button = gr.Button("📋 List")

            save_status = gr.Textbox(label="Status", lines=2)

        with gr.Column(scale=1):
            gr.Markdown("### Formatted Prompt")
            formatted_output = gr.Textbox(
                label="Formatted Prompt (sent to API)",
                lines=8,
                interactive=False
            )

            gr.Markdown("### Response")
            response_output = gr.Textbox(
                label="API Response",
                lines=15,
                interactive=False
            )

    # JavaScript to handle dynamic variable inputs
    template_input.change(
        fn=update_variables_from_template,
        inputs=[template_input, var_configs_state],
        outputs=[var_configs_state, detected_vars_display]
    )

    parse_button.click(
        fn=update_variables_from_template,
        inputs=[template_input, var_configs_state],
        outputs=[var_configs_state, detected_vars_display]
    )

    # Test button
    test_button.click(
        fn=test_prompt_with_vars,
        inputs=[template_input, var_configs_state, model_dropdown, temperature_slider, max_tokens_slider],
        outputs=[formatted_output, response_output, save_status]
    )

    # Template management
    save_button.click(
        fn=save_template,
        inputs=[template_input, template_name_input, var_configs_state],
        outputs=save_status
    )

    load_button.click(
        fn=load_template,
        inputs=template_name_input,
        outputs=[template_input, var_configs_state, save_status]
    )

    list_button.click(
        fn=list_templates,
        outputs=save_status
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
