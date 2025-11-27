import gradio as gr
import os
from openai import OpenAI
from dotenv import load_dotenv
import json

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

def format_prompt(template: str, variables: str) -> str:
    """
    Format the prompt template with variables.
    Variables should be in JSON format.
    """
    try:
        if variables.strip():
            vars_dict = json.loads(variables)
            return template.format(**vars_dict)
        return template
    except json.JSONDecodeError as e:
        return f"Error parsing variables JSON: {e}"
    except KeyError as e:
        return f"Error: Missing variable {e} in template"

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

def test_prompt(template: str, variables: str, model: str, temperature: float, max_tokens: int):
    """
    Test the prompt with the given parameters.
    """
    # Format the prompt
    formatted_prompt = format_prompt(template, variables)

    # If there was an error formatting, return it
    if formatted_prompt.startswith("Error"):
        return formatted_prompt, formatted_prompt, ""

    # Call OpenAI
    response = call_openai(formatted_prompt, model, temperature, max_tokens)

    return formatted_prompt, response, ""

def save_template(template: str, name: str):
    """
    Save a prompt template to file.
    """
    if not name:
        return "Please provide a template name"

    os.makedirs("templates", exist_ok=True)
    filepath = f"templates/{name}.txt"

    with open(filepath, "w") as f:
        f.write(template)

    return f"Template saved to {filepath}"

def load_template(name: str):
    """
    Load a prompt template from file.
    """
    if not name:
        return "Please provide a template name"

    filepath = f"templates/{name}.txt"

    if not os.path.exists(filepath):
        return f"Template {filepath} not found"

    with open(filepath, "r") as f:
        return f.read()

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

# Create Gradio interface
with gr.Blocks(title="Prompt Engineer") as demo:
    gr.Markdown("# 🎯 Prompt Engineer")
    gr.Markdown("Iterate on your AI prompts quickly without restarting the app!")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Prompt Template")
            template_input = gr.Textbox(
                label="Prompt Template",
                placeholder="Enter your prompt template here. Use {variable_name} for variables.",
                lines=10,
                value="You are a helpful assistant.\n\nUser question: {question}"
            )

            gr.Markdown("### Input Variables (JSON)")
            variables_input = gr.Textbox(
                label="Variables",
                placeholder='{"question": "What is the capital of France?"}',
                lines=5,
                value='{"question": "What is the capital of France?"}'
            )

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

    # Connect the test button
    test_button.click(
        fn=test_prompt,
        inputs=[template_input, variables_input, model_dropdown, temperature_slider, max_tokens_slider],
        outputs=[formatted_output, response_output, save_status]
    )

    # Connect template management buttons
    save_button.click(
        fn=save_template,
        inputs=[template_input, template_name_input],
        outputs=save_status
    )

    load_button.click(
        fn=load_template,
        inputs=template_name_input,
        outputs=template_input
    )

    list_button.click(
        fn=list_templates,
        outputs=save_status
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
