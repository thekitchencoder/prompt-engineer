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
        for var_name, var in template.variables.items():
            variables_info += f"### {var_name}\n"
            variables_info += f"**Type:** {var.type.value}\n\n"

            if var.description:
                variables_info += f"*{var.description}*\n\n"

            if var.type.value == "file":
                variables_info += f"**File:** `{var.content}`\n\n"
            else:
                variables_info += f"**Value:**\n```\n{var.content}\n```\n\n"

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

                        # Prompt Selection
                        with gr.Row():
                            prompt_selector = gr.Dropdown(
                                label="Select Prompt",
                                choices=[],
                                interactive=True,
                                scale=4
                            )
                            load_prompt_btn = gr.Button("🔄 Load", scale=1)

                        prompt_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=1,
                            show_label=False
                        )

                        # System Prompt Section
                        with gr.Accordion("System Prompt", open=True):
                            system_file_header = gr.Markdown("*No file loaded*")
                            system_prompt_display = gr.Code(
                                label="",
                                language="markdown",
                                lines=8,
                                interactive=False
                            )

                        # User Prompt Section
                        with gr.Accordion("User Prompt", open=True):
                            user_file_header = gr.Markdown("*No file loaded*")
                            user_prompt_display = gr.Code(
                                label="",
                                language="markdown",
                                lines=8,
                                interactive=False
                            )

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
            """Load prompt and return with file headers."""
            system_content, user_content, vars_info, status = load_prompt_set(prompt_name)

            workspace = workspace_manager.get_current_workspace()
            if workspace and prompt_name:
                prompt_set = workspace.get_prompt_set(prompt_name)
                if prompt_set:
                    # Get file names for headers
                    system_file = ""
                    user_file = ""

                    if 'system' in prompt_set.prompts:
                        system_file = f"📄 `{prompt_set.prompts['system'].path.name}`"

                    if 'user' in prompt_set.prompts:
                        user_file = f"📄 `{prompt_set.prompts['user'].path.name}`"

                    return system_file, system_content, user_file, user_content, vars_info, status

            return "*No file*", system_content, "*No file*", user_content, vars_info, status

        # Load prompt
        load_prompt_btn.click(
            fn=load_and_display_prompt,
            inputs=[prompt_selector],
            outputs=[
                system_file_header,
                system_prompt_display,
                user_file_header,
                user_prompt_display,
                variables_display,
                prompt_status
            ]
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
