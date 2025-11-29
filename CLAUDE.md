# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prompt Engineer is a developer workbench for rapid AI prompt engineering iteration. It's designed for building AI-enabled applications (not chat interfaces) where prompts are compiled into the application with variables interpolated at runtime.

### Core Concept: Workspace-Centric Architecture

**Key Insight**: Prompts live in your application's source code, NOT in Prompt Engineer. This tool points to prompt files in your app's repo and edits them in-place.

**Current State (v0.1)**: Single-file Gradio app with basic template management.

**Target State (v1.0+)**: Workspace-based tool that:
- Opens SpringBoot/Python/Node.js projects
- Auto-discovers prompt files using conventions
- Edits prompts in-place (no sync needed)
- Leverages git for version control
- Supports prompt chaining for evaluator-optimizer patterns

**Important Documents**:
- **[ROADMAP.md](./ROADMAP.md)**: Full feature roadmap with implementation phases
- **[DESIGN.md](./DESIGN.md)**: Detailed architecture and design decisions

## Development Commands

### Running the Application
```bash
python app.py
```
The app launches on `http://localhost:7860` by default.

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup
```bash
cp .env.example .env
# Edit .env with your provider configuration
```

## Architecture

### Single-File Application
The entire application is contained in `app.py` (~750 lines). There are no separate modules or services - all functionality is in one file.

### Core Components

**1. Provider Configuration System**
- `PROVIDER_PRESETS`: Dictionary defining presets for OpenAI, Ollama, LM Studio, OpenRouter, vLLM, and Custom providers
- `config_state`: Global dictionary holding runtime configuration (API key, base URL, provider name, models, defaults)
- Configuration is persisted to `.env` file using `python-dotenv`'s `set_key()` function
- The app can fetch available models from any OpenAI-compatible API endpoint via `fetch_available_models()`

**2. Variable System**
The app supports a custom variable configuration format:
- **Format**: `variable_name:type:content`
- **Types**:
  - `file` - loads content from a file path (e.g., `context:file:variables/sample_context.md`)
  - `value` - uses a fixed text value (e.g., `question:value:What is AI?`)
- Variables are extracted from templates using `{variable_name}` syntax
- Key functions:
  - `parse_variable_config()`: Parses the config format into a dictionary
  - `build_variables_dict()`: Resolves file references and builds final variable values
  - `format_prompt()`: Applies variables to template using Python's `.format()`

**3. Template Management**
- Templates are saved as paired files in `templates/` directory:
  - `{name}.txt` - the prompt template
  - `{name}.vars` - the variable configuration
- Functions: `save_template()`, `load_template()`, `list_templates()`

**4. LLM Integration**
- Uses OpenAI Python SDK (`openai` package) for all providers
- `initialize_client()`: Creates OpenAI client with current config (base_url and api_key)
- `call_llm_api_full()`: Makes API calls and returns both formatted and raw responses
- `process_thinking_response()`: Handles reasoning model responses with `<think>` tags, extracting and formatting them for display

**5. Gradio UI Structure**
The UI is organized into collapsible sections:
- **Configuration Panel**: Provider settings, model selection, defaults (opens automatically on first run if not configured)
- **Main Panel**: Two-column layout
  - Left: Prompt template, variable config, template management
  - Right: Model selector, formatted prompt preview, API response (with Tabs for formatted/raw views)

### Event Flow

**Test Prompt Flow**:
1. User clicks "Test Prompt" button
2. `format_and_prepare()` immediately formats and displays the prompt, shows "Calling API..." message
3. `.then()` chains `call_api_async()` which makes the actual API call
4. Response updates both formatted (Markdown) and raw (JSON) views simultaneously

**Configuration Flow**:
1. User selects provider preset → `update_config_from_preset()` updates all fields
2. User clicks "Load Models from Provider" → `fetch_available_models()` queries API
3. User selects models and defaults → `save_config_with_models()` persists to `.env`
4. `config_state` dict is updated in-memory and client is reinitialized

### File System Structure

```
prompt-engineer/
├── app.py                  # Main application (all code here)
├── requirements.txt        # Dependencies: gradio, openai, python-dotenv
├── .env                   # User configuration (git-ignored)
├── .env.example           # Configuration template
├── templates/             # Saved prompt templates
│   ├── *.txt             # Template files
│   └── *.vars            # Variable configuration files
└── variables/             # Reusable variable content
    ├── sample_context.md
    ├── sample_requirements.yaml
    ├── sample_code.py
    └── sample_data.md
```

## Key Implementation Details

### Gradio Version
The app uses Gradio 6 (as indicated by recent commits migrating from `gr.Box` to `gr.Column` for compatibility). When working with UI components, use Gradio 6 patterns.

### Model Selection
There are TWO model dropdowns:
1. **Config Model** (in Settings): Sets the default model saved to `.env`
2. **Session Model** (in main UI): Used for current session testing, doesn't change config default

Both share the same choices list but serve different purposes.

### Response Views
The app shows API responses in two formats:
- **Formatted tab**: Rendered Markdown with special handling for thinking tags from reasoning models
- **Raw tab**: Complete JSON response object from the API

The Tab switching uses Gradio's Tabs component (migrated from radio toggle in recent commits).

### Environment Variables
All configuration is stored in `.env`:
- `OPENAI_API_KEY`: API key (or "not-needed" for local models)
- `OPENAI_BASE_URL`: Custom endpoint URL (empty for OpenAI)
- `PROVIDER_NAME`: Display name in UI
- `AVAILABLE_MODELS`: Comma-separated list of models
- `DEFAULT_MODEL`: Default model to select
- `DEFAULT_TEMPERATURE`: Default temperature (0.7)
- `DEFAULT_MAX_TOKENS`: Default max tokens (1000)

## Common Modification Patterns

### Adding a New Provider Preset
Add an entry to `PROVIDER_PRESETS` dict with: `base_url`, `api_key_required`, `default_models`, `api_key_placeholder`.

### Modifying Variable Parsing
Edit `parse_variable_config()` to handle new variable types. Currently supports `file` and `value` types.

### Changing UI Layout
All UI is defined in the `with gr.Blocks()` context starting at line ~399. Event handlers are wired up after component definitions.

### Adding Response Processing
Modify `process_thinking_response()` or add new processing in `call_llm_api_full()` to handle special response formats.

---

## Migration to v1.0 (Workspace Architecture)

The current codebase (app.py) will be completely refactored following the roadmap. Key changes:

### Breaking Changes (No Backward Compatibility Required)
- Current template storage (`templates/` directory) will be replaced by workspace model
- `.env` configuration will be supplemented by `workspace.yaml`
- File format will change from `.txt`/`.vars` to language-specific (`.st` for SpringBoot)

### Migration Strategy (Phase 1, Sprint 1-2)
1. **Preserve existing app.py** as `app_old.py` (reference implementation)
2. **Create new modular architecture** in `src/prompt_engineer/`
3. **Build workspace system** first (core foundation)
4. **Migrate UI components** incrementally
5. **Test with real SpringBoot project** before deprecating old code

### Key Architectural Shifts
- **From**: Templates owned by Prompt Engineer
- **To**: Prompts owned by user's application repo
- **From**: Custom variable config format
- **To**: YAML-based, language-agnostic config
- **From**: Hardcoded `{var}` syntax
- **To**: Configurable delimiters per workspace
- **From**: All-in-one app.py
- **To**: Modular `src/prompt_engineer/` packages

See ROADMAP.md Section "Sprint 1-2" for detailed implementation plan.
