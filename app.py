"""
Prompt Engineer - Modern Workspace UI

A developer workbench for rapid prompt engineering iteration with workspace-centric architecture.
"""

import gradio as gr
from pathlib import Path
from typing import Optional, List, Tuple
import os

# Import modular components
from src.prompt_engineer.workspace.workspace import Workspace, WorkspaceManager, WorkspaceError
from src.prompt_engineer.workspace.config import WorkspacePresets, WorkspaceConfig
from src.prompt_engineer.workspace.discovery import ProjectType, ProjectDetector, PromptSet
from src.prompt_engineer.providers.base import LLMRequest, Message, MessageRole
from src.prompt_engineer.providers.registry import ProviderRegistry
from src.prompt_engineer.templates.models import PromptRole
from src.prompt_engineer.config.settings import load_env_config

# Global state
workspace_manager = WorkspaceManager()
provider_registry = ProviderRegistry()


# ============================================================================
# Workspace Management Functions
# ============================================================================

def detect_project_info(workspace_path: str) -> Tuple[str, str, str]:
    """
    Detect project type and suggest configuration.

    Returns:
        Tuple of (project_type, suggested_prompt_dir, suggested_vars_dir)
    """
    if not workspace_path or not Path(workspace_path).exists():
        return "unknown", "prompts", "prompts/vars"

    path = Path(workspace_path)
    project_type = ProjectDetector.detect(path)
    layout = ProjectDetector.suggest_layout(project_type)

    return (
        project_type.value,
        layout.get("prompt_dir", "prompts"),
        layout.get("vars_dir", "prompts/vars")
    )


def create_workspace(
    workspace_path: str,
    workspace_name: str,
    preset: str
) -> Tuple[str, str, str, List[str], str]:
    """
    Create a new workspace with the specified preset.

    Returns:
        Tuple of (status, header, nav_list, prompt_choices, config_info)
    """
    try:
        if not workspace_path:
            return "❌ Please select a workspace directory", "## No Workspace Open", "*No prompts*", [], ""

        if not workspace_name:
            workspace_name = Path(workspace_path).name

        # Create workspace
        workspace = workspace_manager.create_workspace(
            root_path=Path(workspace_path),
            name=workspace_name,
            preset=preset.lower() if preset != "Auto-detect" else None
        )

        # Discover prompts
        prompt_sets = workspace.discover_prompts()
        warnings = workspace.get_warnings()

        # Build status message
        status = f"✅ Workspace created: {workspace.config.name}\n"
        status += f"📁 Root: {workspace.root_path}\n"

        if warnings:
            status += "\n⚠️ Warnings:\n"
            for warning in warnings:
                status += f"  {warning}\n"

        # Build navigation data
        header = get_workspace_header()
        nav_list = format_prompts_list_nav(prompt_sets)
        prompt_choices = get_prompt_names()
        config_info = format_workspace_info(workspace)

        return status, header, nav_list, prompt_choices, config_info

    except Exception as e:
        return f"❌ Error creating workspace: {str(e)}", "## No Workspace Open", "*No prompts*", [], ""


def open_workspace(workspace_path: str) -> Tuple[str, str, str, List[str], str]:
    """
    Open an existing workspace.

    Returns:
        Tuple of (status, header, nav_list, prompt_choices, config_info)
    """
    try:
        if not workspace_path:
            return "❌ Please select a workspace directory", "## No Workspace Open", "*No prompts*", [], ""

        # Open workspace
        workspace = workspace_manager.open_workspace(Path(workspace_path))

        # Discover prompts
        prompt_sets = workspace.discover_prompts()
        warnings = workspace.get_warnings()

        # Build status message
        status = f"✅ Workspace opened: {workspace.config.name}\n"
        status += f"📁 Root: {workspace.root_path}\n"

        if warnings:
            status += "\n⚠️ Warnings:\n"
            for warning in warnings:
                status += f"  {warning}\n"

        # Build navigation data
        header = get_workspace_header()
        nav_list = format_prompts_list_nav(prompt_sets)
        prompt_choices = get_prompt_names()
        config_info = format_workspace_info(workspace)

        return status, header, nav_list, prompt_choices, config_info

    except WorkspaceError as e:
        return f"❌ {str(e)}", "## No Workspace Open", "*No prompts*", [], ""
    except Exception as e:
        return f"❌ Error opening workspace: {str(e)}", "## No Workspace Open", "*No prompts*", [], ""


def format_workspace_info(workspace: Workspace) -> str:
    """Format workspace information for display."""
    config = workspace.config

    info = f"# {config.name}\n\n"

    if config.template.variable_delimiters:
        delim = config.template.variable_delimiters
        info += f"**Variable Syntax:** `{delim.start}variable{delim.end}`\n\n"

    info += "## Configuration\n\n"
    info += f"- **Prompt Directory:** `{config.layout.prompt_dir}`\n"
    info += f"- **Variables Directory:** `{config.layout.vars_dir}`\n"
    info += f"- **Prompt Extension:** `{config.layout.prompt_extension}`\n"
    info += f"- **Variable Extension:** `{config.layout.vars_extension}`\n\n"

    info += "## Naming Convention\n\n"
    info += f"- **Pattern:** `{config.template.naming.pattern}`\n"
    info += f"- **Roles:** {', '.join(config.template.naming.roles)}\n\n"

    info += "## Default Model\n\n"
    info += f"- **Provider:** {config.defaults.provider}\n"
    info += f"- **Model:** {config.defaults.model}\n"
    info += f"- **Temperature:** {config.defaults.temperature}\n"
    info += f"- **Max Tokens:** {config.defaults.max_tokens}\n"

    return info


def format_prompt_list(prompt_sets: List[PromptSet]) -> str:
    """Format prompt sets for display."""
    if not prompt_sets:
        return "No prompts found. Add prompt files to your workspace to get started."

    output = "# Discovered Prompts\n\n"

    matched = [ps for ps in prompt_sets if not ps.is_orphaned]
    orphaned = [ps for ps in prompt_sets if ps.is_orphaned]

    if matched:
        output += "## Matched Prompts\n\n"
        for ps in matched:
            output += f"### {ps.name}\n\n"

            if ps.var_file:
                output += f"**Variable File:** `{ps.var_file.path.name}`\n\n"

            output += "**Prompts:**\n"
            for role, prompt_file in ps.prompts.items():
                output += f"- **{role}**: `{prompt_file.path.name}`\n"

            output += "\n"

    if orphaned:
        output += "## ⚠️ Orphaned Prompts\n\n"
        output += "*These prompts don't have matching variable files.*\n\n"
        for ps in orphaned:
            for role, prompt_file in ps.prompts.items():
                output += f"- `{prompt_file.path.name}`\n"
        output += "\n"

    return output


def load_prompt_set(prompt_name: str) -> Tuple[str, str, str, str]:
    """
    Load a specific prompt set for viewing/editing.

    Returns:
        Tuple of (system_prompt, user_prompt, variables_info, status)
    """
    workspace = workspace_manager.get_current_workspace()
    if not workspace:
        return "", "", "", "❌ No workspace open"

    try:
        # Get prompt set
        prompt_set = workspace.get_prompt_set(prompt_name)
        if not prompt_set:
            return "", "", "", f"❌ Prompt set '{prompt_name}' not found"

        # Check if this is a single-file prompt (role="prompt")
        if "prompt" in prompt_set.prompts and len(prompt_set.prompts) == 1:
            # Single-file prompt - load into user prompt field
            prompt_file = prompt_set.prompts["prompt"]
            with open(prompt_file.path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Load variables if available
            variables_info = "## Variables\n\n*No variables configured*"
            if prompt_set.var_file:
                template = workspace.load_template(prompt_name)
                if template and template.variables:
                    variables_info = "## Variables\n\n"
                    for var_name, var in template.variables.items():
                        variables_info += f"### {var_name}\n"
                        variables_info += f"**Type:** {var.type.value}\n\n"
                        if var.description:
                            variables_info += f"*{var.description}*\n\n"
                        if var.type.value == "file":
                            variables_info += f"**File:** `{var.content}`\n\n"
                        else:
                            variables_info += f"**Value:**\n```\n{var.content}\n```\n\n"

            return "", content, variables_info, f"✅ Loaded single-file prompt: {prompt_name}"

        # Multi-role prompt (system + user)
        # Load template
        template = workspace.load_template(prompt_name)
        if not template:
            return "", "", "", f"❌ Could not load template '{prompt_name}'"

        # Load prompt contents
        system_prompt = ""
        user_prompt = ""

        if template.has_prompt(PromptRole.SYSTEM):
            system_prompt_obj = template.get_prompt(PromptRole.SYSTEM)
            system_prompt = system_prompt_obj.get_content(workspace.root_path)

        if template.has_prompt(PromptRole.USER):
            user_prompt_obj = template.get_prompt(PromptRole.USER)
            user_prompt = user_prompt_obj.get_content(workspace.root_path)

        # Format variables
        variables_info = "## Variables\n\n"
        if template.variables:
            for var_name, var in template.variables.items():
                variables_info += f"### {var_name}\n"
                variables_info += f"**Type:** {var.type.value}\n\n"

                if var.description:
                    variables_info += f"*{var.description}*\n\n"

                if var.type.value == "file":
                    variables_info += f"**File:** `{var.content}`\n\n"
                else:
                    variables_info += f"**Value:**\n```\n{var.content}\n```\n\n"
        else:
            variables_info += "*No variables configured*"

        status = f"✅ Loaded prompt set: {prompt_name}"

        return system_prompt, user_prompt, variables_info, status

    except Exception as e:
        return "", "", "", f"❌ Error loading prompt: {str(e)}"


def get_prompt_names() -> List[str]:
    """Get list of available prompt names from current workspace."""
    workspace = workspace_manager.get_current_workspace()
    if not workspace:
        return []

    try:
        prompt_sets = workspace.discover_prompts()
        # Filter out orphaned prompts for the dropdown
        matched = [ps.name for ps in prompt_sets if not ps.is_orphaned]
        return matched
    except Exception:
        # Return empty list if discovery fails
        return []


def save_prompt_file(prompt_name: str, role: str, content: str) -> str:
    """
    Save prompt content back to file.

    Args:
        prompt_name: Name of the prompt set
        role: Role (system/user/prompt)
        content: New content to save

    Returns:
        Status message
    """
    workspace = workspace_manager.get_current_workspace()
    if not workspace:
        return "❌ No workspace open"

    try:
        # Get prompt set to find file path
        prompt_set = workspace.get_prompt_set(prompt_name)
        if not prompt_set:
            return f"❌ Prompt set '{prompt_name}' not found"

        # For single-file prompts, map "user" role to "prompt" role
        if "prompt" in prompt_set.prompts and role == "user":
            role = "prompt"

        # Find the prompt file for this role
        if role not in prompt_set.prompts:
            return f"❌ No {role} prompt found for '{prompt_name}'"

        prompt_file = prompt_set.prompts[role]
        file_path = prompt_file.path

        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"✅ Saved {role} prompt to {file_path.name}"

    except Exception as e:
        return f"❌ Error saving prompt: {str(e)}"


def extract_variables_from_prompt(content: str) -> List[str]:
    """
    Extract variable names from prompt content.

    Args:
        content: Prompt template content

    Returns:
        List of variable names
    """
    workspace = workspace_manager.get_current_workspace()
    if not workspace:
        return []

    # Get delimiter from workspace config
    config = workspace.config
    start_delim = config.template.variable_delimiters.start
    end_delim = config.template.variable_delimiters.end

    # Use the parser from workspace
    return workspace.parser.extract_variables(content)


def create_new_prompt(prompt_name: str, prompt_type: str) -> Tuple[str, List[str], str]:
    """
    Create a new prompt set with system/user prompts and variable file.

    Args:
        prompt_name: Name for the new prompt (e.g., "code_review")
        prompt_type: Type of prompt structure ("single" or "multi-role")

    Returns:
        Tuple of (status_message, updated_prompt_choices, updated_nav_list)
    """
    workspace = workspace_manager.get_current_workspace()
    if not workspace:
        return "❌ No workspace open", [], "*No prompts*"

    if not prompt_name or not prompt_name.strip():
        return "❌ Please enter a prompt name", [], "*No prompts*"

    # Sanitize prompt name (remove spaces, special chars)
    import re
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', prompt_name.strip().lower())

    try:
        config = workspace.config
        prompt_dir = workspace.root_path / config.layout.prompt_dir
        vars_dir = workspace.root_path / config.layout.vars_dir

        # Create directories if they don't exist
        prompt_dir.mkdir(parents=True, exist_ok=True)
        vars_dir.mkdir(parents=True, exist_ok=True)

        prompt_ext = config.layout.prompt_extension
        vars_ext = config.layout.vars_extension

        if prompt_type == "multi-role":
            # Create system and user prompt files
            system_file = prompt_dir / f"system-{safe_name}{prompt_ext}"
            user_file = prompt_dir / f"user-{safe_name}{prompt_ext}"

            if system_file.exists() or user_file.exists():
                return f"❌ Prompt '{safe_name}' already exists", get_prompt_names(), format_prompts_list_nav(workspace.discover_prompts())

            # Write system prompt template
            system_file.write_text(
                f"You are a helpful assistant.\n\n"
                f"{{context}}\n\n"
                f"Please help with the following task.",
                encoding='utf-8'
            )

            # Write user prompt template
            user_file.write_text(
                f"{{user_request}}\n\n"
                f"Please provide a detailed response.",
                encoding='utf-8'
            )

            created_files = f"system-{safe_name}{prompt_ext}, user-{safe_name}{prompt_ext}"

        else:  # single file
            prompt_file = prompt_dir / f"{safe_name}{prompt_ext}"

            if prompt_file.exists():
                return f"❌ Prompt '{safe_name}' already exists", get_prompt_names(), format_prompts_list_nav(workspace.discover_prompts())

            # Write single prompt template
            prompt_file.write_text(
                f"{{input}}\n\n"
                f"Please provide a response to the above.",
                encoding='utf-8'
            )

            created_files = f"{safe_name}{prompt_ext}"

        # Create variable file
        var_file = vars_dir / f"{safe_name}{vars_ext}"
        if not var_file.exists():
            # Create a basic YAML variable file with valid structure
            var_file.write_text(
                f"# Variable configuration for {safe_name}\n"
                f"description: \"Prompt for {safe_name}\"\n"
                f"variables: {{}}\n"
                f"  # Add your variables here. Example:\n"
                f"  # variable_name:\n"
                f"  #   type: file  # or 'value'\n"
                f"  #   path: path/to/file.txt  # for type: file\n"
                f"  #   # OR\n"
                f"  #   value: \"text content\"  # for type: value\n"
                f"  #   description: \"Variable description\"\n",
                encoding='utf-8'
            )

        # Trigger re-discovery
        prompt_sets = workspace.discover_prompts()
        nav_list = format_prompts_list_nav(prompt_sets)

        return (
            f"✅ Created new prompt: {created_files}\n"
            f"📝 Variable file: {safe_name}{vars_ext}",
            get_prompt_names(),
            nav_list
        )

    except Exception as e:
        return f"❌ Error creating prompt: {str(e)}", get_prompt_names(), "*No prompts*"


def initialize_workspace() -> Tuple[str, Workspace]:
    """
    Auto-initialize workspace for current directory.

    Returns:
        Tuple of (status_message, workspace)
    """
    current_dir = Path.cwd()

    try:
        # Try to open existing workspace
        workspace = workspace_manager.open_workspace(current_dir)
        # Verify workspace is valid by accessing config
        _ = workspace.config
        return f"✅ Loaded workspace from {current_dir.name}", workspace
    except (WorkspaceError, Exception):
        # No workspace exists or invalid, create one
        workspace = workspace_manager.create_workspace(
            root_path=current_dir,
            name=current_dir.name,
            preset=None  # Auto-detect
        )
        return f"✅ Initialized workspace in {current_dir.name}", workspace


def get_workspace_header() -> str:
    """Get workspace header info for display."""
    workspace = workspace_manager.get_current_workspace()
    if not workspace:
        return "*Initializing workspace...*"

    try:
        config = workspace.config
        return f"**{config.name}** | `{workspace.root_path.name}`"
    except:
        return "*Initializing workspace...*"


def format_prompts_list_nav(prompt_sets: List[PromptSet]) -> str:
    """Format prompts for left navigation panel."""
    if not prompt_sets:
        return "*No prompts discovered*"

    output = ""
    matched = [ps for ps in prompt_sets if not ps.is_orphaned]
    orphaned = [ps for ps in prompt_sets if ps.is_orphaned]

    for ps in matched:
        roles = ", ".join(ps.prompts.keys())
        output += f"• **{ps.name}** ({roles})\n"

    if orphaned:
        output += f"\n*{len(orphaned)} orphaned prompt(s)*\n"

    return output


# ============================================================================
# Gradio UI
# ============================================================================

def create_ui():
    """Create the Gradio UI with icon-based navigation."""

    with gr.Blocks(title="Prompt Engineer") as app:

        # ================================================================
        # Main Layout: Icon Nav + Content Area
        # ================================================================
        with gr.Row():
            # ================================================================
            # LEFT ICON NAVIGATION (minimal)
            # ================================================================
            with gr.Column(scale=0, min_width=60):
                gr.Markdown("### 🛠️")

                # Navigation buttons (icon-only style)
                prompts_nav_btn = gr.Button("📝", size="lg", variant="primary")
                llm_nav_btn = gr.Button("🤖", size="lg")
                settings_nav_btn = gr.Button("⚙️", size="lg")

            # ================================================================
            # MAIN CONTENT AREA
            # ================================================================
            with gr.Column(scale=1):

                # Top Bar
                with gr.Row():
                    workspace_info = gr.Markdown(get_workspace_header())

                # ============================================================
                # VIEW 1: PROMPT/VARIABLE EDITOR
                # ============================================================
                with gr.Column(visible=True) as prompts_view:
                    gr.Markdown("## 📝 Prompt & Variable Editor")

                    # Prompt Selection
                    with gr.Row():
                        prompt_selector = gr.Dropdown(
                            label="Select Prompt",
                            choices=get_prompt_names(),
                            interactive=True,
                            scale=3
                        )
                        create_new_btn = gr.Button("➕ New", size="sm", scale=1)

                    # Role and File Management
                    with gr.Row():
                        with gr.Column(scale=1):
                            prompt_role_selector = gr.Radio(
                                label="Role",
                                choices=["system", "user", "assistant"],
                                value="user"
                            )
                        with gr.Column(scale=2):
                            prompt_file_info = gr.Markdown("*No file selected*")

                    # Tabbed Editor (Prompt + Variables)
                    with gr.Tabs():
                        with gr.Tab("Prompt"):
                            prompt_editor = gr.Textbox(
                                label="",
                                placeholder="Enter prompt content...",
                                lines=15,
                                max_lines=25,
                                interactive=True,
                                show_label=False
                            )
                            with gr.Row():
                                with gr.Column(scale=1):
                                    save_prompt_btn = gr.Button("💾 Save", variant="primary")
                                with gr.Column(scale=3):
                                    prompt_vars_display = gr.Markdown("*No variables detected*")

                        with gr.Tab("Variables"):
                            variables_editor = gr.Textbox(
                                label="Variable Configuration (YAML)",
                                placeholder="# Define variables here\nvariables:\n  var_name:\n    type: value\n    value: \"content\"",
                                lines=15,
                                max_lines=25,
                                interactive=True
                            )
                            save_vars_btn = gr.Button("💾 Save Variables", variant="primary")

                    editor_status = gr.Textbox(label="Status", interactive=False, lines=1, show_label=False)

                # ============================================================
                # VIEW 2: LLM COMPOSITION & TESTING
                # ============================================================
                with gr.Column(visible=False) as llm_view:
                    gr.Markdown("## 🤖 LLM Testing")

                    # Model Selection
                    with gr.Row():
                        model_dropdown = gr.Dropdown(
                            label="Model",
                            choices=["gpt-4", "gpt-3.5-turbo", "claude-3-opus"],
                            value="gpt-4",
                            scale=2
                        )
                        temperature_slider = gr.Slider(
                            label="Temperature",
                            minimum=0,
                            maximum=2,
                            value=0.7,
                            step=0.1,
                            scale=1
                        )

                    # Prompt Composition
                    gr.Markdown("### Compose Prompt")
                    with gr.Row():
                        system_prompt_selector = gr.Dropdown(
                            label="System Prompt",
                            choices=get_prompt_names(),
                            allow_custom_value=True
                        )
                        user_prompt_selector = gr.Dropdown(
                            label="User Prompt",
                            choices=get_prompt_names(),
                            allow_custom_value=True
                        )

                    # Raw View & Send
                    with gr.Tabs():
                        with gr.Tab("Raw Request"):
                            raw_request_display = gr.Code(
                                label="",
                                language="json",
                                lines=10
                            )

                        with gr.Tab("Response"):
                            llm_response_display = gr.Markdown("*No response yet*")

                        with gr.Tab("Raw Response"):
                            raw_response_display = gr.Code(
                                label="",
                                language="json",
                                lines=10
                            )

                    send_to_llm_btn = gr.Button("🚀 Send to LLM", variant="primary", size="lg")
                    llm_status = gr.Textbox(label="Status", interactive=False, lines=1, show_label=False)

                # ============================================================
                # VIEW 3: SETTINGS
                # ============================================================
                with gr.Column(visible=False) as settings_view:
                    gr.Markdown("## ⚙️ Settings")

                    with gr.Accordion("Workspace Configuration", open=True):
                        workspace_config_display = gr.Code(
                            label="workspace.yaml",
                            language="yaml",
                            lines=15
                        )

                    with gr.Accordion("Provider Configuration", open=False):
                        gr.Markdown("*Provider settings coming soon*")

        # ================================================================
        # Event Handlers
        # ================================================================

        # Navigation
        def show_prompts_view():
            return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

        def show_llm_view():
            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)

        def show_settings_view():
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

        prompts_nav_btn.click(
            fn=show_prompts_view,
            outputs=[prompts_view, llm_view, settings_view]
        )

        llm_nav_btn.click(
            fn=show_llm_view,
            outputs=[prompts_view, llm_view, settings_view]
        )

        settings_nav_btn.click(
            fn=show_settings_view,
            outputs=[prompts_view, llm_view, settings_view]
        )

        # Prompt Editor
        def load_prompt_for_editing(prompt_name):
            """Load a prompt for editing."""
            if not prompt_name:
                return "", "*No file selected*", "*No variables*", ""

            workspace = workspace_manager.get_current_workspace()
            if not workspace:
                return "", "*No workspace*", "*No variables*", "❌ No workspace"

            try:
                prompt_set = workspace.get_prompt_set(prompt_name)
                if not prompt_set:
                    return "", "*Not found*", "*No variables*", f"❌ Prompt '{prompt_name}' not found"

                # Load first available prompt (single-file or first role)
                content = ""
                file_name = ""

                if 'prompt' in prompt_set.prompts:
                    prompt_file = prompt_set.prompts['prompt']
                    file_name = prompt_file.path.name
                elif 'user' in prompt_set.prompts:
                    prompt_file = prompt_set.prompts['user']
                    file_name = prompt_file.path.name
                elif 'system' in prompt_set.prompts:
                    prompt_file = prompt_set.prompts['system']
                    file_name = prompt_file.path.name
                else:
                    # Get first available
                    prompt_file = list(prompt_set.prompts.values())[0]
                    file_name = prompt_file.path.name

                with open(prompt_file.path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract variables
                vars_list = extract_variables_from_prompt(content)
                vars_md = "*No variables detected*"
                if vars_list:
                    vars_md = "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in vars_list])

                file_info = f"📄 `{file_name}`"

                return content, file_info, vars_md, f"✅ Loaded {prompt_name}"

            except Exception as e:
                return "", "*Error*", "*No variables*", f"❌ Error: {str(e)}"

        prompt_selector.change(
            fn=load_prompt_for_editing,
            inputs=[prompt_selector],
            outputs=[prompt_editor, prompt_file_info, prompt_vars_display, editor_status]
        )

        # Save prompt (simplified - saves to currently selected file)
        def save_current_prompt(prompt_name, content):
            """Save the current prompt content."""
            return save_prompt_file(prompt_name, "user", content)  # Default to user for now

        save_prompt_btn.click(
            fn=save_current_prompt,
            inputs=[prompt_selector, prompt_editor],
            outputs=[editor_status]
        )

        # Live variable extraction
        def update_vars_display(content):
            vars_list = extract_variables_from_prompt(content)
            if vars_list:
                return "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in vars_list])
            return "*No variables detected*"

        prompt_editor.change(
            fn=update_vars_display,
            inputs=[prompt_editor],
            outputs=[prompt_vars_display]
        )

    return app



# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Load environment configuration
    load_env_config()

    # Initialize workspace
    try:
        init_status, workspace = initialize_workspace()
        print(init_status)
    except Exception as e:
        print(f"⚠️ Warning: {str(e)}")
        print("⚠️ Continuing without workspace...")

    # Create and launch UI
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
