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
├── prompt_engineer/           # Main package
│   ├── __init__.py
│   ├── app.py                # Gradio UI with 4 accordion sections
│   ├── config.py             # User + workspace config management
│   ├── prompts.py            # Prompt file operations, interpolation
│   └── llm.py                # LLM provider integration, API calls
├── setup.py                   # CLI installation
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
- `list_prompt_files()`: Discover `.txt` files in prompt directory
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

**Section 1: User Configuration**
- Provider dropdown (presets)
- API key and base URL inputs
- Load models from provider
- Model selection and defaults (temperature, max_tokens)
- Save to `~/.prompt-engineer/config.yaml`
- Auto-collapses if config exists

**Section 2: Workspace Configuration**
- Workspace name
- Paths: prompts directory, data directory
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
- Model override
- Temperature/max_tokens sliders
- Tabs: Formatted Response | Raw Request | Raw Response
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
name: "My Workspace"
paths:
  prompts: "prompts"
  data: "prompt-data"
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
- Tabs for different views (Editor/Preview, Formatted/Raw)
- Real-time updates via `.change()` event handlers
- Status bars for validation feedback

### Error Handling
- Config validation before save
- File existence checks for variable files
- Unmapped variable detection in prompts
- API error messages with helpful context

## Common Modification Patterns

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
