.. _architecture:

Architecture
============

Prompt Engineer follows a modular architecture with clear separation of concerns.

Core Modules
------------

The application is organized into four main modules:

config.py - Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Handles user and workspace configuration:

* **User Config** (``~/.prompt-engineer/config.yaml``)

  * Provider settings (OpenAI, Ollama, etc.)
  * API credentials
  * Model preferences
  * Default parameters

* **Workspace Config** (``${workspace}/.prompt-engineer/workspace.yaml``)

  * Prompt directory paths
  * Variable mappings (file or value types)
  * Workspace-specific overrides

prompts.py - Prompt Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Manages prompt files and variable interpolation:

* File discovery and listing
* Content loading and saving
* Variable extraction using ``{var_name}`` syntax
* Template interpolation with error handling
* Validation of prompt variables

llm.py - LLM Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

Provides LLM provider integration:

* OpenAI-compatible client initialization
* Model discovery from provider APIs
* API calls with error handling
* Thinking tag processing for reasoning models
* Token and cost estimation

app.py - Gradio UI
~~~~~~~~~~~~~~~~~~

Web interface with 4 accordion sections:

1. **User Configuration**

   * Provider presets and API settings
   * Model selection and defaults
   * Change tracking for save button

2. **Workspace Configuration**

   * Prompt directory paths
   * Variable management UI
   * Real-time validation

3. **Prompt Editor**

   * File selection dropdown
   * Editor and preview tabs
   * Variable status display
   * Save with change tracking

4. **LLM Interaction**

   * Two-phase execution (prepare → execute)
   * Request, Response, and Output tabs
   * Model parameter controls
   * Status tracking

Key Design Patterns
-------------------

Workspace-Centric Approach
~~~~~~~~~~~~~~~~~~~~~~~~~~

Prompts live in your application's source code, not in Prompt Engineer. The tool:

* Points to prompt files in your repository
* Edits files in-place
* Uses git-friendly configuration files

Variable System
~~~~~~~~~~~~~~~

Two variable types for flexible content management:

* **File variables**: Reference external files (code, data, context)
* **Value variables**: Inline text stored in workspace config

Change Tracking
~~~~~~~~~~~~~~~

Save buttons use hidden state to detect changes:

1. Store original values in hidden state
2. Compare current values on change events
3. Enable/disable save button accordingly
4. Update state after successful save

Two-Phase Execution
~~~~~~~~~~~~~~~~~~~

LLM interaction splits prepare and execute:

1. **Phase 1**: Build request payload (immediate display)
2. **Phase 2**: Execute API call (async with progress)

This provides immediate feedback while the request is being prepared.

Configuration Sync
~~~~~~~~~~~~~~~~~~

User config changes automatically sync to LLM test section:

* Model dropdown updates
* Temperature slider updates
* Max tokens slider updates
* No page reload required

Error Handling
--------------

Comprehensive error handling throughout:

* Config validation before save
* File existence checks
* API error messages with context
* Unmapped variable detection
* Network error handling with retry logic

Future Considerations
---------------------

See ``archive/ROADMAP.md`` for future enhancements:

* Chain workflows (evaluator-optimizer patterns)
* Git integration for status awareness
* File watchers for automatic refresh
* Migration to Svelte + FastAPI for better UI control
* Advanced syntax highlighting with Monaco Editor
