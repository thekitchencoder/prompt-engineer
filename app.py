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
) -> Tuple[str, str, str]:
    """
    Create a new workspace with the specified preset.

    Returns:
        Tuple of (status_message, workspace_info, prompt_list)
    """
    try:
        if not workspace_path:
            return "❌ Please select a workspace directory", "", ""

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
        status += f"📝 Prompt directory: {workspace.config.layout.prompt_dir}\n"
        status += f"📋 Variables directory: {workspace.config.layout.vars_dir}\n"

        if warnings:
            status += "\n⚠️ Warnings:\n"
            for warning in warnings:
                status += f"  {warning}\n"

        # Build workspace info
        info = format_workspace_info(workspace)

        # Build prompt list
        prompt_list = format_prompt_list(prompt_sets)

        return status, info, prompt_list

    except Exception as e:
        return f"❌ Error creating workspace: {str(e)}", "", ""


def open_workspace(workspace_path: str) -> Tuple[str, str, str]:
    """
    Open an existing workspace.

    Returns:
        Tuple of (status_message, workspace_info, prompt_list)
    """
    try:
        if not workspace_path:
            return "❌ Please select a workspace directory", "", ""

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

        # Build workspace info
        info = format_workspace_info(workspace)

        # Build prompt list
        prompt_list = format_prompt_list(prompt_sets)

        return status, info, prompt_list

    except WorkspaceError as e:
        return f"❌ {str(e)}", "", ""
    except Exception as e:
        return f"❌ Error opening workspace: {str(e)}", "", ""


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


# ============================================================================
# Gradio UI
# ============================================================================

def create_ui():
    """Create the Gradio UI."""

    with gr.Blocks(title="Prompt Engineer") as app:

        # Header
        gr.Markdown("# 🛠️ Prompt Engineer - Developer Workbench")
        gr.Markdown("*Workspace-centric prompt engineering for AI-enabled applications*")

        # Main tabs
        with gr.Tabs() as main_tabs:

            # ================================================================
            # Workspace Tab
            # ================================================================
            with gr.Tab("📁 Workspace"):
                gr.Markdown("## Open or Create a Workspace")
                gr.Markdown(
                    "Point to your application's root directory. "
                    "Prompt Engineer will auto-detect the project type and discover prompts."
                )

                with gr.Row():
                    with gr.Column(scale=2):
                        workspace_path = gr.Textbox(
                            label="Workspace Directory",
                            placeholder="/path/to/your/app",
                            value=str(Path.cwd()),
                            info="Root directory of your application"
                        )

                    with gr.Column(scale=1):
                        detect_btn = gr.Button("🔍 Detect Project", size="sm")

                # Auto-detection results
                with gr.Row():
                    detected_type = gr.Textbox(
                        label="Detected Project Type",
                        interactive=False,
                        scale=1
                    )
                    suggested_prompt_dir = gr.Textbox(
                        label="Suggested Prompt Directory",
                        interactive=False,
                        scale=1
                    )
                    suggested_vars_dir = gr.Textbox(
                        label="Suggested Variables Directory",
                        interactive=False,
                        scale=1
                    )

                # Workspace creation/opening
                gr.Markdown("### Configure Workspace")

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
                    create_btn = gr.Button("➕ Create New Workspace", variant="primary")
                    open_btn = gr.Button("📂 Open Existing Workspace", variant="secondary")

                # Status message
                workspace_status = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=5
                )

                # Workspace info display
                with gr.Row():
                    with gr.Column(scale=1):
                        workspace_info = gr.Markdown("*No workspace open*")

                    with gr.Column(scale=1):
                        prompt_list = gr.Markdown("*No prompts discovered*")

            # ================================================================
            # Prompts Tab
            # ================================================================
            with gr.Tab("📝 Prompts"):
                gr.Markdown("## Prompt Viewer")
                gr.Markdown("*Load and view prompts from your workspace*")

                with gr.Row():
                    prompt_selector = gr.Dropdown(
                        label="Select Prompt",
                        choices=[],
                        interactive=True,
                        scale=3
                    )

                    load_prompt_btn = gr.Button("🔄 Load Prompt", scale=1)
                    refresh_list_btn = gr.Button("🔄 Refresh List", size="sm", scale=1)

                prompt_status = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=2
                )

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### System Prompt")
                        system_prompt_display = gr.Code(
                            label="",
                            language="markdown",
                            lines=10,
                            interactive=False
                        )

                    with gr.Column():
                        gr.Markdown("### User Prompt")
                        user_prompt_display = gr.Code(
                            label="",
                            language="markdown",
                            lines=10,
                            interactive=False
                        )

                gr.Markdown("### Variables")
                variables_display = gr.Markdown("*No variables*")

            # ================================================================
            # Settings Tab
            # ================================================================
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("## Workspace Settings")
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
        create_btn.click(
            fn=create_workspace,
            inputs=[workspace_path, workspace_name, preset_choice],
            outputs=[workspace_status, workspace_info, prompt_list]
        ).then(
            fn=get_prompt_names,
            inputs=[],
            outputs=[prompt_selector]
        )

        # Open workspace
        open_btn.click(
            fn=open_workspace,
            inputs=[workspace_path],
            outputs=[workspace_status, workspace_info, prompt_list]
        ).then(
            fn=get_prompt_names,
            inputs=[],
            outputs=[prompt_selector]
        )

        # Load prompt
        load_prompt_btn.click(
            fn=load_prompt_set,
            inputs=[prompt_selector],
            outputs=[system_prompt_display, user_prompt_display, variables_display, prompt_status]
        )

        # Refresh prompt list
        refresh_list_btn.click(
            fn=get_prompt_names,
            inputs=[],
            outputs=[prompt_selector]
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
