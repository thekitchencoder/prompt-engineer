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

    prompt_sets = workspace.discover_prompts()
    # Filter out orphaned prompts for the dropdown
    matched = [ps.name for ps in prompt_sets if not ps.is_orphaned]
    return matched


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


def get_workspace_header() -> str:
    """Get workspace header info for display."""
    workspace = workspace_manager.get_current_workspace()
    if not workspace:
        return "## No Workspace Open\n\nOpen or create a workspace to get started."

    config = workspace.config
    header = f"## 📁 {config.name}\n\n"
    header += f"**Root:** `{workspace.root_path.name}`\n\n"

    # TODO: Add git branch/status when implemented
    # header += f"**Branch:** `main` ●2\n\n"

    return header


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
    """Create the Gradio UI with modern left-nav layout."""

    with gr.Blocks(title="Prompt Engineer") as app:

        # State to track current workspace/prompt
        current_prompt = gr.State("")

        # ================================================================
        # Main Layout: Left Navigation + Main Workspace
        # ================================================================
        with gr.Row():
            # ================================================================
            # LEFT NAVIGATION PANEL
            # ================================================================
            with gr.Column(scale=1):

                # Workspace Header
                workspace_header = gr.Markdown(
                    "## No Workspace Open\n\nClick 'Open Workspace' below"
                )

                # Open Workspace Button
                open_workspace_btn = gr.Button("📂 Open Workspace", size="sm", variant="primary")

                gr.Markdown("---")

                # Prompts Section
                gr.Markdown("### 📝 Prompts")
                prompts_nav = gr.Markdown("*No prompts*")

                gr.Markdown("---")

                # Chains Section (Placeholder)
                gr.Markdown("### 🔗 Chains")
                gr.Markdown("*Coming soon*")

                gr.Markdown("---")

                # History Section (Placeholder)
                gr.Markdown("### 📊 History")
                gr.Markdown("*Coming soon*")

                gr.Markdown("---")

                # Settings Button
                settings_btn = gr.Button("⚙️ Settings", size="sm")

            # ================================================================
            # MAIN WORKSPACE AREA
            # ================================================================
            with gr.Column(scale=3):

                # Top Bar with Workspace Info
                with gr.Row():
                    gr.Markdown("# 🛠️ Prompt Engineer")
                    workspace_info_header = gr.Markdown("*No workspace open*")

                gr.Markdown("---")

                # Main Content Tabs
                with gr.Tabs() as main_tabs:

                    # ============================================================
                    # Workspace Setup Tab (shown when no workspace is open)
                    # ============================================================
                    with gr.Tab("📁 Workspace Setup", id="workspace_setup"):
                        gr.Markdown("## Open or Create a Workspace")
                        gr.Markdown(
                            "Point to your application's root directory. "
                            "Prompt Engineer will auto-detect the project type and discover prompts."
                        )

                        with gr.Row():
                            workspace_path = gr.Textbox(
                                label="Workspace Directory",
                                placeholder="/path/to/your/app",
                                value=str(Path.cwd()),
                                info="Root directory of your application",
                                scale=3
                            )
                            detect_btn = gr.Button("🔍 Detect", size="sm", scale=1)

                        # Auto-detection results
                        with gr.Row():
                            detected_type = gr.Textbox(
                                label="Detected Type",
                                interactive=False,
                                scale=1
                            )
                            suggested_prompt_dir = gr.Textbox(
                                label="Prompt Directory",
                                interactive=False,
                                scale=1
                            )
                            suggested_vars_dir = gr.Textbox(
                                label="Variables Directory",
                                interactive=False,
                                scale=1
                            )

                        # Workspace creation/opening
                        with gr.Row():
                            workspace_name = gr.Textbox(
                                label="Workspace Name",
                                placeholder="My Application Prompts",
                                scale=2
                            )
                            preset_choice = gr.Dropdown(
                                label="Preset",
                                choices=["Auto-detect", "SpringBoot", "Python", "Node.js", "Custom"],
                                value="Auto-detect",
                                scale=1
                            )

                        with gr.Row():
                            create_workspace_btn = gr.Button("➕ Create New Workspace", variant="primary")
                            open_existing_btn = gr.Button("📂 Open Existing Workspace", variant="secondary")

                        workspace_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=4
                        )

                    # ============================================================
                    # Prompt Editor Tab
                    # ============================================================
                    with gr.Tab("📝 Prompt Editor", id="prompt_editor"):

                        # Prompt Selection and Creation
                        with gr.Row():
                            prompt_selector = gr.Dropdown(
                                label="Select Prompt",
                                choices=[],
                                interactive=True,
                                scale=3
                            )
                            load_prompt_btn = gr.Button("🔄 Load", scale=1)
                            create_new_btn = gr.Button("➕ New", size="sm", variant="secondary", scale=1)

                        # Create New Prompt Dialog (collapsed by default)
                        with gr.Accordion("Create New Prompt", open=False, visible=False) as create_prompt_accordion:
                            with gr.Row():
                                new_prompt_name = gr.Textbox(
                                    label="Prompt Name",
                                    placeholder="e.g., code_review, data_analysis",
                                    scale=2
                                )
                                new_prompt_type = gr.Radio(
                                    label="Type",
                                    choices=["single", "multi-role"],
                                    value="multi-role",
                                    info="Single=one file, Multi-role=system+user files",
                                    scale=1
                                )

                            create_confirm_btn = gr.Button("✅ Create Prompt", variant="primary")

                        prompt_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=1,
                            show_label=False
                        )

                        # System Prompt Section
                        with gr.Accordion("System Prompt", open=True):
                            with gr.Row():
                                system_file_header = gr.Markdown("*No file loaded*")

                            system_prompt_display = gr.Textbox(
                                label="",
                                placeholder="System prompt content...",
                                lines=10,
                                max_lines=20,
                                interactive=True,
                                show_label=False
                            )

                            with gr.Row():
                                save_system_btn = gr.Button("💾 Save System Prompt", size="sm", variant="primary")
                                system_vars_display = gr.Markdown("*No variables detected*")

                        # User Prompt Section
                        with gr.Accordion("User Prompt", open=True):
                            with gr.Row():
                                user_file_header = gr.Markdown("*No file loaded*")

                            user_prompt_display = gr.Textbox(
                                label="",
                                placeholder="User prompt content...",
                                lines=10,
                                max_lines=20,
                                interactive=True,
                                show_label=False
                            )

                            with gr.Row():
                                save_user_btn = gr.Button("💾 Save User Prompt", size="sm", variant="primary")
                                user_vars_display = gr.Markdown("*No variables detected*")

                        # Variables Section
                        with gr.Accordion("Variables", open=True):
                            variables_display = gr.Markdown("*No variables*")

                        # Response Section (Placeholder for Task 1.2.6)
                        with gr.Accordion("Response", open=False):
                            gr.Markdown("*Response display coming soon*")
                            gr.Markdown("This will show: Formatted | Raw Request | Raw Response tabs")

                    # ============================================================
                    # Settings Tab
                    # ============================================================
                    with gr.Tab("⚙️ Settings", id="settings"):
                        gr.Markdown("## Workspace Configuration")
                        workspace_config_display = gr.Markdown("*Open a workspace to view configuration*")

                        gr.Markdown("---")

                        gr.Markdown("## Provider Settings")
                        gr.Markdown("*Coming soon: Provider configuration, model settings, etc.*")

        # ================================================================
        # Event Handlers
        # ================================================================

        # Detect project type
        detect_btn.click(
            fn=detect_project_info,
            inputs=[workspace_path],
            outputs=[detected_type, suggested_prompt_dir, suggested_vars_dir]
        )

        # Create workspace
        def handle_create_workspace(path, name, preset):
            status, header, nav_list, prompt_choices, config_info = create_workspace(path, name, preset)
            return status, header, nav_list, gr.update(choices=prompt_choices), config_info

        create_workspace_btn.click(
            fn=handle_create_workspace,
            inputs=[workspace_path, workspace_name, preset_choice],
            outputs=[workspace_status, workspace_header, prompts_nav, prompt_selector, workspace_config_display]
        )

        # Open existing workspace
        def handle_open_workspace(path):
            status, header, nav_list, prompt_choices, config_info = open_workspace(path)
            return status, header, nav_list, gr.update(choices=prompt_choices), config_info

        open_existing_btn.click(
            fn=handle_open_workspace,
            inputs=[workspace_path],
            outputs=[workspace_status, workspace_header, prompts_nav, prompt_selector, workspace_config_display]
        )

        # Open workspace from left nav button
        open_workspace_btn.click(
            fn=lambda: gr.update(selected="workspace_setup"),
            outputs=[main_tabs]
        )

        # Settings button
        settings_btn.click(
            fn=lambda: gr.update(selected="settings"),
            outputs=[main_tabs]
        )

        # Helper function to load and display prompt with file headers
        def load_and_display_prompt(prompt_name):
            """Load prompt and return with file headers and extracted variables."""
            system_content, user_content, vars_info, status = load_prompt_set(prompt_name)

            workspace = workspace_manager.get_current_workspace()
            system_file = "*No file*"
            user_file = "*No file*"
            system_vars_md = "*No variables detected*"
            user_vars_md = "*No variables detected*"

            if workspace and prompt_name:
                prompt_set = workspace.get_prompt_set(prompt_name)
                if prompt_set:
                    # Get file names for headers
                    if 'system' in prompt_set.prompts:
                        system_file = f"📄 `{prompt_set.prompts['system'].path.name}`"
                        # Extract variables from system prompt
                        system_vars = extract_variables_from_prompt(system_content)
                        if system_vars:
                            system_vars_md = "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in system_vars])

                    if 'user' in prompt_set.prompts:
                        user_file = f"📄 `{prompt_set.prompts['user'].path.name}`"
                        # Extract variables from user prompt
                        user_vars = extract_variables_from_prompt(user_content)
                        if user_vars:
                            user_vars_md = "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in user_vars])

                    # Handle single-file prompts (role="prompt")
                    if 'prompt' in prompt_set.prompts:
                        user_file = f"📄 `{prompt_set.prompts['prompt'].path.name}`"
                        # Extract variables from prompt content
                        user_vars = extract_variables_from_prompt(user_content)
                        if user_vars:
                            user_vars_md = "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in user_vars])

            return (
                system_file, system_content, system_vars_md,
                user_file, user_content, user_vars_md,
                vars_info, status
            )

        # Load prompt
        load_prompt_btn.click(
            fn=load_and_display_prompt,
            inputs=[prompt_selector],
            outputs=[
                system_file_header,
                system_prompt_display,
                system_vars_display,
                user_file_header,
                user_prompt_display,
                user_vars_display,
                variables_display,
                prompt_status
            ]
        )

        # Save system prompt
        def save_system_prompt(prompt_name, content):
            """Save system prompt to file."""
            status = save_prompt_file(prompt_name, "system", content)
            # Re-extract variables after save
            vars_list = extract_variables_from_prompt(content)
            vars_md = "*No variables detected*"
            if vars_list:
                vars_md = "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in vars_list])
            return status, vars_md

        save_system_btn.click(
            fn=save_system_prompt,
            inputs=[prompt_selector, system_prompt_display],
            outputs=[prompt_status, system_vars_display]
        )

        # Save user prompt
        def save_user_prompt(prompt_name, content):
            """Save user prompt to file."""
            status = save_prompt_file(prompt_name, "user", content)
            # Re-extract variables after save
            vars_list = extract_variables_from_prompt(content)
            vars_md = "*No variables detected*"
            if vars_list:
                vars_md = "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in vars_list])
            return status, vars_md

        save_user_btn.click(
            fn=save_user_prompt,
            inputs=[prompt_selector, user_prompt_display],
            outputs=[prompt_status, user_vars_display]
        )

        # Live variable extraction as user types (debounced)
        def update_system_vars(content):
            """Update variable display as system prompt is edited."""
            vars_list = extract_variables_from_prompt(content)
            if vars_list:
                return "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in vars_list])
            return "*No variables detected*"

        system_prompt_display.change(
            fn=update_system_vars,
            inputs=[system_prompt_display],
            outputs=[system_vars_display]
        )

        def update_user_vars(content):
            """Update variable display as user prompt is edited."""
            vars_list = extract_variables_from_prompt(content)
            if vars_list:
                return "**Variables:** " + ", ".join([f"`{{{v}}}`" for v in vars_list])
            return "*No variables detected*"

        user_prompt_display.change(
            fn=update_user_vars,
            inputs=[user_prompt_display],
            outputs=[user_vars_display]
        )

        # Create New Prompt functionality
        def toggle_create_dialog():
            """Toggle the create new prompt dialog."""
            return gr.update(visible=True, open=True)

        create_new_btn.click(
            fn=toggle_create_dialog,
            outputs=[create_prompt_accordion]
        )

        def handle_create_new_prompt(name, ptype):
            """Create a new prompt and update UI."""
            status, prompt_choices, nav_list = create_new_prompt(name, ptype)
            return (
                status,
                gr.update(choices=prompt_choices),
                nav_list,  # Update left navigation
                gr.update(visible=False, open=False),  # Hide create dialog
                ""  # Clear name field
            )

        create_confirm_btn.click(
            fn=handle_create_new_prompt,
            inputs=[new_prompt_name, new_prompt_type],
            outputs=[prompt_status, prompt_selector, prompts_nav, create_prompt_accordion, new_prompt_name]
        )

    return app


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Load environment configuration
    load_env_config()

    # Create and launch UI
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
