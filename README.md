# Prompt Engineer

A CLI-based developer workbench for rapid AI prompt engineering iteration.

## Concept

Prompt Engineer is designed for building AI-enabled applications where prompts are compiled into the application with variables interpolated at runtime. It provides a simple, low-friction workflow for:

- Editing prompt templates with variable interpolation
- Managing variable mappings (files or fixed values)
- Testing prompts against multiple LLM providers
- Viewing formatted and raw API responses

**Key Insight**: Prompts live in your application's source code, NOT in Prompt Engineer. This tool points to prompt files in your app's repo and edits them in-place.

## Installation

```bash
# Clone the repository
cd prompt-engineer

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the application
pip install -e .
```

## Quick Start

```bash
# Make sure venv is activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run from your project directory (uses current directory as workspace)
prompt-engineer

# Or specify a workspace directory
prompt-engineer --workspace /path/to/your/project

# Custom port
prompt-engineer --port 8080
```

## Usage

The UI is organized into 4 collapsible accordion sections:

### 1. ⚙️ User Configuration
- **Saved to**: `~/.prompt-engineer/config.yaml`
- **Purpose**: Provider settings, API keys, default models
- **Auto-collapse**: Yes (if already configured)

Configure your LLM provider (OpenAI, Ollama, LM Studio, OpenRouter, etc.), API keys, and default model settings. This configuration is saved globally for your user.

### 2. 📁 Workspace Configuration
- **Saved to**: `${workspace}/.prompt-engineer/workspace.yaml`
- **Purpose**: Workspace paths and variable mappings

Define:
- Prompt directory (where prompt files live - any file extension supported)
- Variable mappings:
  ```yaml
  variables:
    code_to_evaluate:
      type: file
      path: "prompt-data/sample-code.java"

    evaluation_criteria:
      type: value
      value: "Correctness, performance, security"
  ```

### 3. ✏️ Prompt Editor
- Edit prompt template files
- Use `{variable_name}` syntax for variables
- **Two tabs**:
  - **Editor**: Edit the raw template
  - **Interpolated Preview**: See the final prompt with variables substituted

Real-time validation shows unmapped variables and file issues.

### 4. 🚀 LLM Interaction
- Choose system and/or user prompts
- Override model settings if needed
- **Three tabs**:
  - **Formatted Response**: Rendered Markdown
  - **Raw Request**: Exact JSON sent to LLM API
  - **Raw Response**: Full API response object

Status bar shows tokens, estimated cost, and timing.

## Example Workflow

1. **Setup (one-time)**:
   - Configure user settings (API key, provider, models)
   - Define workspace paths (prompts directory, data directory)
   - Map variables to files or values

2. **Daily iteration**:
   - Open prompt editor section
   - Select a prompt file
   - Edit template, see live interpolated preview
   - Save changes
   - Open LLM interaction section
   - Select prompts, run, review responses
   - Iterate!

## File Structure

```
your-project/
├── .prompt-engineer/
│   └── workspace.yaml          # Workspace configuration
├── prompts/                    # Prompt templates
│   ├── system-reviewer.txt
│   └── user-reviewer.txt
└── prompt-data/                # Variable data files
    ├── sample-code.py
    └── criteria.md
```

## Configuration Files

### User Config (`~/.prompt-engineer/config.yaml`)

```yaml
provider: "openai"
api_key: "sk-..."
base_url: ""  # Leave empty for OpenAI

models:
  - "gpt-4o"
  - "gpt-4o-mini"

defaults:
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 2000

presets:
  openai:
    base_url: ""
    api_key_required: true
    default_models: ["gpt-4o", "gpt-4o-mini"]

  ollama:
    base_url: "http://localhost:11434/v1"
    api_key_required: false
    default_models: ["llama3.2", "mistral"]
```

### Workspace Config (`${workspace}/.prompt-engineer/workspace.yaml`)

```yaml
paths:
  prompts: "prompts"

variables:
  code_to_evaluate:
    type: file
    path: "prompt-data/sample-code.java"
    description: "Code to evaluate"  # Optional

  evaluation_criteria:
    type: value
    value: |
      - Code correctness
      - Performance
      - Security

defaults:
  model: "gpt-4o"  # Override user default for this workspace
  temperature: 0.3
```

## Features

- ✅ **Simple CLI installation** - `pip install -e .`
- ✅ **Workspace-centric** - Points to your app's source code
- ✅ **Provider-agnostic** - Works with any OpenAI-compatible API
- ✅ **Variable interpolation** - `{var}` syntax with file or value sources
- ✅ **Live preview** - See interpolated prompts before running
- ✅ **Raw visibility** - See exact request/response JSON
- ✅ **Cost estimation** - Token count and cost estimates
- ✅ **Auto-save** - Changes saved to files automatically

## POC Status

This is a **proof-of-concept** to validate the core workflow:
- Editing prompts in-place (workspace-centric)
- Low-friction variable management
- Clear visibility into LLM interactions

**Not included in POC**:
- Chain workflows (evaluator-optimizer patterns)
- Git integration
- File watchers for external changes
- Advanced UI (tree views, syntax highlighting)

See `archive/ROADMAP.md` for future feature plans.

## Development

```bash
# Install in development mode
pip install -e .

# Run directly
python -m prompt_engineer.app

# Or use CLI
prompt-engineer
```

## License

MIT
