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
            # LEFT ICON NAVIGATION (fixed width)
            # ================================================================
            with gr.Column(scale=0, min_width=80, elem_id="left-nav"):
                gr.Markdown("<br>")  # Top spacing

                # Navigation buttons (icon-only, larger for visibility)
                prompts_nav_btn = gr.Button(
                    "📝",
                    size="lg",
                    variant="primary",  # Active by default
                    elem_id="nav-prompts"
                )
                llm_nav_btn = gr.Button(
                    "🤖",
                    size="lg",
                    variant="secondary",  # Inactive by default
                    elem_id="nav-llm"
                )
                settings_nav_btn = gr.Button(
                    "⚙️",
                    size="lg",
                    variant="secondary",  # Inactive by default
                    elem_id="nav-settings"
                )

            # ================================================================
            # MAIN CONTENT AREA (takes remaining space)
            # ================================================================
            with gr.Column(scale=1, elem_id="main-content"):

                # Top Bar
                with gr.Row():
                    workspace_info = gr.Markdown(get_workspace_header())

                # Use Tabs for proper view switching (hide tab headers with CSS)
                with gr.Tabs(selected=0, elem_id="view-tabs") as view_tabs:
                    # ============================================================
                    # VIEW 1: PROMPT/VARIABLE EDITOR
                    # ============================================================
                    with gr.Tab("Prompts", id=0, elem_id="prompts-tab"):
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

                        # New Prompt Dialog (hidden by default)
                        with gr.Column(visible=False) as new_prompt_dialog:
                            gr.Markdown("### Create New Prompt")
                            with gr.Row():
                                new_prompt_name = gr.Textbox(
                                    label="Prompt Name",
                                    placeholder="e.g., code_review",
                                    scale=3
                                )
                            with gr.Row():
                                create_prompt_btn = gr.Button("Create", variant="primary", scale=1)
                                cancel_create_btn = gr.Button("Cancel", scale=1)

                        # File Info
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

                        editor_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=2,
                            max_lines=5,
                            show_label=False,
                            container=False
                        )

                        # Hidden state to track unsaved changes
                        original_prompt_content = gr.State("")
                        original_vars_content = gr.State("")

                    # ============================================================
                    # VIEW 2: LLM COMPOSITION & TESTING
                    # ============================================================
                    with gr.Tab("LLM", id=1, elem_id="llm-tab"):
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
                    with gr.Tab("Settings", id=2, elem_id="settings-tab"):
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

        # Navigation - switch tabs and update button variants
        def show_prompts_view():
            return (
                gr.Tabs(selected=0),  # Select Prompts tab
                gr.update(variant="primary"),  # prompts_nav_btn active
                gr.update(variant="secondary"),  # llm_nav_btn inactive
                gr.update(variant="secondary")   # settings_nav_btn inactive
            )

        def show_llm_view():
            return (
                gr.Tabs(selected=1),  # Select LLM tab
                gr.update(variant="secondary"),  # prompts_nav_btn inactive
                gr.update(variant="primary"),    # llm_nav_btn active
                gr.update(variant="secondary")   # settings_nav_btn inactive
            )

        def show_settings_view():
            return (
                gr.Tabs(selected=2),  # Select Settings tab
                gr.update(variant="secondary"),  # prompts_nav_btn inactive
                gr.update(variant="secondary"),  # llm_nav_btn inactive
                gr.update(variant="primary")     # settings_nav_btn active
            )

        prompts_nav_btn.click(
            fn=show_prompts_view,
            outputs=[view_tabs, prompts_nav_btn, llm_nav_btn, settings_nav_btn]
        )

        llm_nav_btn.click(
            fn=show_llm_view,
            outputs=[view_tabs, prompts_nav_btn, llm_nav_btn, settings_nav_btn]
        )

        settings_nav_btn.click(
            fn=show_settings_view,
            outputs=[view_tabs, prompts_nav_btn, llm_nav_btn, settings_nav_btn]
        )

        # Prompt Editor
        def load_prompt_for_editing(prompt_name):
            """Load a prompt for editing."""
            if not prompt_name:
                return "", "*No file selected*", "*No variables*", "", "", "", ""

            workspace = workspace_manager.get_current_workspace()
            if not workspace:
                return "", "*No workspace*", "*No variables*", "", "", "", ""

            try:
                prompt_set = workspace.get_prompt_set(prompt_name)
                if not prompt_set:
                    return "", "*Not found*", "*No variables*", "", f"❌ Prompt '{prompt_name}' not found", "", ""

                # Load variables if available
                var_content = ""
                if prompt_set.var_file:
                    try:
                        with open(prompt_set.var_file.path, 'r', encoding='utf-8') as f:
                            var_content = f.read()
                    except:
                        var_content = ""

                # Get the first available prompt file
                if not prompt_set.prompts:
                    return "", "*No prompt files*", "*No variables*", var_content, f"❌ No prompt files for '{prompt_name}'", "", var_content

                # Load the first prompt file (or 'prompt' if it exists)
                prompt_file = None
                if 'prompt' in prompt_set.prompts:
                    prompt_file = prompt_set.prompts['prompt']
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

                return content, file_info, vars_md, var_content, f"✅ Loaded {prompt_name}", content, var_content

            except Exception as e:
                return "", "*Error*", "*No variables*", "", f"❌ Error: {str(e)}", "", ""

        # Check for unsaved changes
        def check_dirty_state(current_prompt, original_prompt, current_vars, original_vars):
            """Check if there are unsaved changes and update status."""
            prompt_changed = current_prompt != original_prompt
            vars_changed = current_vars != original_vars

            if prompt_changed and vars_changed:
                return "⚠️ Prompt and Variables have unsaved changes"
            elif prompt_changed:
                return "⚠️ Prompt has unsaved changes"
            elif vars_changed:
                return "⚠️ Variables have unsaved changes"
            else:
                return ""

        # Trigger load on prompt selection change
        prompt_selector.change(
            fn=load_prompt_for_editing,
            inputs=[prompt_selector],
            outputs=[prompt_editor, prompt_file_info, prompt_vars_display, variables_editor, editor_status, original_prompt_content, original_vars_content]
        )

        # Save prompt
        def save_current_prompt(prompt_name, content):
            """Save the current prompt content."""
            if not prompt_name:
                return "❌ No prompt selected", content

            workspace = workspace_manager.get_current_workspace()
            if not workspace:
                return "❌ No workspace open", content

            try:
                prompt_set = workspace.get_prompt_set(prompt_name)
                if not prompt_set:
                    return f"❌ Prompt set '{prompt_name}' not found", content

                # Get the first prompt file to save to
                prompt_file = None
                if 'prompt' in prompt_set.prompts:
                    prompt_file = prompt_set.prompts['prompt']
                else:
                    prompt_file = list(prompt_set.prompts.values())[0]

                # Write content to file
                with open(prompt_file.path, 'w', encoding='utf-8') as f:
                    f.write(content)

                return f"✅ Saved to {prompt_file.path.name}", content

            except Exception as e:
                return f"❌ Error saving prompt: {str(e)}", content

        save_prompt_btn.click(
            fn=save_current_prompt,
            inputs=[prompt_selector, prompt_editor],
            outputs=[editor_status, original_prompt_content]
        )

        # Save variables YAML file
        def save_variables_file(prompt_name, var_content):
            """Save the variables YAML file."""
            workspace = workspace_manager.get_current_workspace()
            if not workspace:
                return "❌ No workspace open", var_content

            if not prompt_name:
                return "❌ No prompt selected", var_content

            try:
                prompt_set = workspace.get_prompt_set(prompt_name)
                if not prompt_set:
                    return f"❌ Prompt set '{prompt_name}' not found", var_content

                # Get or create variable file path
                if prompt_set.var_file:
                    var_file_path = prompt_set.var_file.path
                else:
                    # Create new variable file
                    config = workspace.config
                    vars_dir = workspace.root_path / config.layout.vars_dir
                    vars_dir.mkdir(parents=True, exist_ok=True)
                    vars_ext = config.layout.vars_extension
                    var_file_path = vars_dir / f"{prompt_name}{vars_ext}"

                # Write content
                with open(var_file_path, 'w', encoding='utf-8') as f:
                    f.write(var_content)

                return f"✅ Saved variables to {var_file_path.name}", var_content

            except Exception as e:
                return f"❌ Error saving variables: {str(e)}", var_content

        save_vars_btn.click(
            fn=save_variables_file,
            inputs=[prompt_selector, variables_editor],
            outputs=[editor_status, original_vars_content]
        )

        # Combined function for prompt editor changes
        def on_prompt_change(content, original_prompt, current_vars, original_vars):
            """Update variable display and check dirty state."""
            # Extract variables
            vars_list = extract_variables_from_prompt(content)
            if vars_list:
                vars_md = "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in vars_list])
            else:
                vars_md = "*No variables detected*"

            # Check dirty state
            status = check_dirty_state(content, original_prompt, current_vars, original_vars)

            return vars_md, status

        # Track changes in prompt editor
        prompt_editor.change(
            fn=on_prompt_change,
            inputs=[prompt_editor, original_prompt_content, variables_editor, original_vars_content],
            outputs=[prompt_vars_display, editor_status]
        )

        # Track changes in variables editor
        variables_editor.change(
            fn=check_dirty_state,
            inputs=[prompt_editor, original_prompt_content, variables_editor, original_vars_content],
            outputs=[editor_status]
        )

        # New Prompt Dialog handlers
        def show_create_dialog():
            """Show the create new prompt dialog."""
            return gr.update(visible=True)

        def hide_create_dialog():
            """Hide the create new prompt dialog."""
            return gr.update(visible=False)

        def clear_and_hide():
            """Clear the name field and hide dialog."""
            return gr.update(visible=False), ""

        def handle_create_prompt(name):
            """Create a new prompt and refresh the list."""
            status, updated_choices, _ = create_new_prompt(name, "single")
            # Get the safe name that was actually created
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip().lower())
            # Hide dialog, clear name field, update dropdown with new prompt selected, show status
            return (
                gr.update(visible=False),
                "",
                gr.update(choices=updated_choices, value=safe_name),
                status
            )

        create_new_btn.click(
            fn=show_create_dialog,
            outputs=[new_prompt_dialog]
        )

        cancel_create_btn.click(
            fn=hide_create_dialog,
            outputs=[new_prompt_dialog]
        )

        create_prompt_btn.click(
            fn=handle_create_prompt,
            inputs=[new_prompt_name],
            outputs=[new_prompt_dialog, new_prompt_name, prompt_selector, editor_status]
        )

        # Trigger initial load if a prompt is selected
        def on_app_load():
            """Load the first prompt on app startup."""
            prompt_names = get_prompt_names()
            if prompt_names:
                # Load the first prompt
                return load_prompt_for_editing(prompt_names[0])
            # Return empty values
            return "", "*No prompts found*", "*No variables*", "", "", "", ""

        app.load(
            fn=on_app_load,
            outputs=[prompt_editor, prompt_file_info, prompt_vars_display, variables_editor, editor_status, original_prompt_content, original_vars_content]
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

    # Custom CSS for navigation and view switching
    custom_css = """
    #left-nav {
        max-width: 80px !important;
        min-width: 80px !important;
        flex-grow: 0 !important;
        flex-shrink: 0 !important;
    }
    #nav-prompts, #nav-llm, #nav-settings {
        font-size: 32px !important;
        min-width: 60px !important;
        max-width: 60px !important;
        height: 60px !important;
        padding: 8px !important;
    }
    /* Hide the tab headers */
    #view-tabs .tab-nav {
        display: none !important;
    }
    #view-tabs > .tabs {
        display: none !important;
    }
    #view-tabs button[role="tab"] {
        display: none !important;
    }
    """

    # Create and launch UI
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=custom_css
    )
