# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prompt Engineer is a CLI-based developer workbench for rapid AI prompt engineering iteration. It's designed for building AI-enabled applications (not chat interfaces) where prompts are compiled into the application with variables interpolated at runtime.

### Core Concept: Workspace-Centric Architecture

**Key Insight**: Prompts live in your application's source code, NOT in Prompt Engineer. This tool points to prompt files in your app's repo and edits them in-place.

**Current State (v0.1 POC)**: CLI-based tool with modular architecture, testing core workflow concepts.

**Archived Documents** (future vision):
- **[archive/ROADMAP.md](./archive/ROADMAP.md)**: Full feature roadmap with implementation phases
- **[archive/DESIGN.md](./archive/DESIGN.md)**: Detailed architecture and design decisions

## Development Commands

### Installation
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode (installs all dependencies)
pip install -e .
```

### Running the Application
```bash
# Make sure venv is activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run using CLI command
prompt-engineer

# Or specify workspace
prompt-engineer --workspace /path/to/project

# Custom port
prompt-engineer --port 8080

# Alternative: Run as Python module
python -m prompt_engineer.app
```

### Testing
```bash
# Create test workspace
mkdir -p /tmp/test-workspace/prompts /tmp/test-workspace/prompt-data

# Run against test workspace
prompt-engineer --workspace /tmp/test-workspace
```

## Architecture

### Modular POC Structure
The application is organized into a Python package with clear separation of concerns:

```
prompt-engineer/
├── src/
│   └── prompt_engineer/      # Main package
│       ├── __init__.py
│       ├── app.py            # Gradio UI with 4 accordion sections
│       ├── config.py         # User + workspace config management
│       ├── prompts.py        # Prompt file operations, interpolation
│       └── llm.py            # LLM provider integration, API calls
├── pyproject.toml            # Package configuration and CLI installation
├── requirements.txt
├── app_old.py                # Original single-file reference
└── archive/                  # Archived docs
    ├── ROADMAP.md
    ├── DESIGN.md
    └── src/                  # Previous modular attempt
```

### Core Modules

**1. config.py - Configuration Management**
- `load_user_config()` / `save_user_config()`: User-level settings (`~/.prompt-engineer/config.yaml`)
- `load_workspace_config()` / `save_workspace_config()`: Workspace settings (`${workspace}/.prompt-engineer/workspace.yaml`)
- `validate_user_config()` / `validate_workspace_config()`: Validation logic
- Supports provider presets (OpenAI, Ollama, LM Studio, OpenRouter)

**2. prompts.py - Prompt Operations**
- `list_prompt_files()`: Discover all files in prompt directory (any extension, excludes hidden files and directories)
- `load_prompt_file()` / `save_prompt_file()`: File I/O
- `extract_variables()`: Find `{var_name}` patterns in templates
- `interpolate_prompt()`: Replace variables with values from config
- `load_variable_value()`: Resolve file or value variable types

**3. llm.py - LLM Integration**
- `initialize_client()`: Create OpenAI-compatible client
- `fetch_available_models()`: Query provider API for models
- `call_llm_api()`: Execute prompt and return formatted/raw responses
- `process_thinking_response()`: Handle `<think>` tags from reasoning models
- `estimate_tokens()` / `estimate_cost()`: Usage analytics

**4. app.py - Gradio UI (4 Accordion Sections)**

Key UI Functions:
- `check_user_config_changes()`: Detects changes in user config fields for button state
- `save_user_config_ui()`: Saves config and syncs LLM test section controls
- `prepare_request_ui()`: Builds request payload and displays immediately
- `execute_request_ui()`: Executes LLM API call and displays response
- `check_prompt_changes()`: Detects changes in prompt editor for button state
- `refresh_all_ui()`: Comprehensive refresh of prompts, variables, and validation

**Section 1: User Configuration**
- Provider dropdown (presets)
- API key and base URL inputs
- Load models from provider
- Model selection and defaults (temperature, max_tokens)
- Save button with change tracking (disabled when no changes made)
- Auto-syncs LLM test section when saved
- Save to `~/.prompt-engineer/config.yaml`
- Auto-collapses if config exists

**Section 2: Workspace Configuration**
- Paths: prompts directory
- Variable mappings (add/edit/remove)
- Variable table display
- Save to `${workspace}/.prompt-engineer/workspace.yaml`
- Real-time validation

**Section 3: Prompt Editor**
- Dropdown: select prompt file
- Tabs: Editor | Interpolated Preview
- Real-time variable extraction
- Status bar: unmapped variables, file issues
- Save changes to file

**Section 4: LLM Interaction**
- System prompt dropdown (optional)
- User prompt dropdown (required)
- Model, temperature, max_tokens (synced from user config defaults)
- Tabs: Request | Response | Output
  - **Request**: Raw JSON payload displayed immediately on button click
  - **Response**: Complete API response (shown after completion)
  - **Output**: Formatted markdown with syntax highlighting
- Two-phase execution: prepare request (instant) → execute API call (async)
- Status: tokens, cost, timing

### Configuration Files

**User Config** (`~/.prompt-engineer/config.yaml`):
```yaml
provider: "openai"
api_key: "sk-..."
base_url: ""
models: ["gpt-4o", "gpt-4o-mini"]
defaults:
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 2000
presets:
  openai: {...}
  ollama: {...}
```

**Workspace Config** (`${workspace}/.prompt-engineer/workspace.yaml`):
```yaml
paths:
  prompts: "prompts"
variables:
  my_var:
    type: file
    path: "prompt-data/file.txt"
  another_var:
    type: value
    value: "fixed text"
```

## Key Implementation Details

### Variable Syntax
- Uses `{variable_name}` syntax (Python `.format()` style)
- Extracted via regex: `r'\{(\w+)\}'`
- Future: Support configurable delimiters per workspace

### Variable Types
1. **file**: Load content from file path (relative to workspace root)
   ```yaml
   my_var:
     type: file
     path: "prompt-data/file.txt"
   ```

2. **value**: Fixed text value (inline in YAML)
   ```yaml
   my_var:
     type: value
     value: "inline text"
   ```

### Response Processing
- **Formatted**: Markdown rendering with syntax highlighting
- **Raw Request**: Full JSON payload sent to API (for debugging)
- **Raw Response**: Complete API response object
- **Thinking tags**: Special handling for `<think>...</think>` from reasoning models

### Gradio UI Patterns
- **Gradio 6**: Uses Gradio 6 (theme passed to `.launch()`, not `Blocks()`)
- Uses Accordion components for collapsible sections
- Tabs for different views (Editor/Preview, Request/Response/Output)
- Real-time updates via `.change()` event handlers
- Status bars for validation feedback
- **Change tracking pattern**: Save buttons use hidden state to track original values
  - Buttons start disabled (no changes)
  - Enable when current values differ from original
  - Disable after successful save
  - Used in: User Config section, Prompt Editor section
- **Two-phase execution**: LLM interaction splits prepare/execute for immediate feedback
  - Phase 1: Build and display request payload immediately
  - Phase 2: Execute API call and display response asynchronously
  - Chained via `.then()` in event handlers

### Error Handling
- Config validation before save
- File existence checks for variable files
- Unmapped variable detection in prompts
- API error messages with helpful context

## Common Modification Patterns

### Understanding Config Synchronization
The app maintains sync between User Config (Section 1) and LLM Test section (Section 4):
- When user config is saved, LLM test controls update to match new defaults
- Model dropdown, temperature slider, and max_tokens slider all sync
- This eliminates the need for page reload to see config changes
- Implementation: `save_user_config_ui()` returns `gr.update()` objects for all synced controls

### Adding a New Provider Preset
Edit `config.py` → `get_default_user_config()` → `presets` dict:
```python
"my-provider": {
    "base_url": "http://localhost:8000/v1",
    "api_key_required": False,
    "default_models": ["model1", "model2"],
}
```

### Adding a New Variable Type
1. Edit `prompts.py` → `load_variable_value()` to handle new type
2. Update workspace config YAML schema
3. Add UI controls in Section 2 (workspace config)

### Modifying UI Layout
Edit `app.py` → `create_ui()`:
- Accordions are defined with `gr.Accordion()`
- Event handlers are wired at the end of each section
- Use `.change()`, `.click()`, etc. for reactivity

### Implementing Change Tracking for Save Buttons
To add change tracking to a new save button (pattern used in User Config & Prompt Editor):

1. Create a hidden state to track original values:
   ```python
   original_state = gr.State(value=initial_values)
   ```

2. Initialize save button as disabled:
   ```python
   save_btn = gr.Button("Save", interactive=False)
   ```

3. Create a check function that compares current vs original:
   ```python
   def check_changes(current_val, original_val):
       return gr.update(interactive=(current_val != original_val))
   ```

4. Wire change handlers to all input fields:
   ```python
   for component in [field1, field2, field3]:
       component.change(
           fn=check_changes,
           inputs=[field1, field2, field3, original_state],
           outputs=[save_btn],
           show_progress="hidden"
       )
   ```

5. Update state and disable button after save:
   ```python
   save_btn.click(fn=save_function, ...).then(
       fn=lambda: new_values.copy(),
       outputs=[original_state]
   ).then(
       fn=lambda: gr.update(interactive=False),
       outputs=[save_btn]
   )
   ```

### Adding New LLM Provider Support
Edit `llm.py`:
- `initialize_client()` creates OpenAI-compatible client
- Works with any API following OpenAI spec
- Add pricing to `estimate_cost()` if needed

## POC Status & Next Steps

### What This POC Validates
1. ✅ Workspace-centric approach (prompts in source code)
2. ✅ Low-friction variable management (YAML config)
3. ✅ Clear LLM interaction visibility (raw request/response)
4. ✅ CLI-based workflow

### Known Limitations
- No chain workflows (evaluator-optimizer patterns)
- No git integration
- No file watchers (manual refresh required)
- Basic UI (no syntax highlighting, tree views)
- No undo/redo

### If POC Succeeds, Consider
1. Add chain workflows (see `archive/DESIGN.md` for spec)
2. Migrate to Svelte + FastAPI for better UI control
3. Add git status awareness
4. Implement file watchers
5. Add syntax highlighting (Monaco Editor)

### If POC Fails, Re-evaluate
- Is workspace-centric approach the right model?
- Is variable management still too manual?
- Do users need more visual tools?

See `archive/ROADMAP.md` for full feature vision.
