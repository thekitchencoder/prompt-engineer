.. _configuration:

Configuration
=============

Prompt Engineer uses two levels of configuration: user-level and workspace-level.

User Configuration
------------------

Location: ``~/.prompt-engineer/config.yaml``

The user config stores global settings that apply across all workspaces.

Structure
~~~~~~~~~

.. code-block:: yaml

    provider: "openai"
    api_key: "sk-..."
    base_url: ""
    models:
      - "gpt-4o"
      - "gpt-4o-mini"
      - "gpt-3.5-turbo"
    defaults:
      model: "gpt-4o"
      temperature: 0.7
      max_tokens: 2000

Provider Presets
~~~~~~~~~~~~~~~~

Built-in presets for common providers:

**OpenAI**

.. code-block:: yaml

    provider: "openai"
    base_url: ""
    api_key: "sk-..."  # Required

**Ollama (Local)**

.. code-block:: yaml

    provider: "ollama"
    base_url: "http://localhost:11434/v1"
    api_key: ""  # Not required

**LM Studio (Local)**

.. code-block:: yaml

    provider: "lm-studio"
    base_url: "http://localhost:1234/v1"
    api_key: ""  # Not required

**OpenRouter**

.. code-block:: yaml

    provider: "openrouter"
    base_url: "https://openrouter.ai/api/v1"
    api_key: "sk-or-..."  # Required

Workspace Configuration
-----------------------

Location: ``${workspace}/.prompt-engineer/workspace.yaml``

The workspace config stores project-specific settings.

Structure
~~~~~~~~~

.. code-block:: yaml

    paths:
      prompts: "prompts"

    variables:
      code_sample:
        type: file
        path: "prompt-data/sample.py"

      concept:
        type: value
        value: "recursion"

    defaults:
      model: ""  # Empty = use user default
      temperature: null  # null = use user default

Variable Types
~~~~~~~~~~~~~~

**File Variables**

Load content from external files:

.. code-block:: yaml

    my_variable:
      type: file
      path: "relative/path/to/file.txt"

* Path is relative to workspace root
* File content is loaded at interpolation time
* Supports any text file format

**Value Variables**

Inline text values:

.. code-block:: yaml

    my_variable:
      type: value
      value: "Some inline text content"

* Value stored directly in config
* Good for short, frequently-used text
* Easy to version control

Validation
----------

User Config Validation
~~~~~~~~~~~~~~~~~~~~~~

Checks performed on save:

* Provider is specified
* API key present (if required by provider)
* At least one model configured
* Valid YAML syntax

Workspace Config Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Checks performed on save:

* Prompt directory exists
* Variable file paths exist (for file-type variables)
* Valid YAML syntax
* No circular variable references

Configuration Precedence
------------------------

When multiple sources define the same setting:

1. **Workspace config** (highest priority)
2. **User config**
3. **Built-in defaults** (lowest priority)

Example: If workspace config specifies a default model, it overrides the user config default model.

Best Practices
--------------

**User Config**

* Store API keys securely
* Use provider presets for consistency
* Keep common models in the list
* Set reasonable defaults

**Workspace Config**

* Commit to version control
* Use relative paths for portability
* Document variable purpose in comments
* Keep sensitive data in files (not inline values)

**Security**

* Never commit API keys to git
* Use ``.gitignore`` for sensitive files
* Consider using environment variables for API keys (future enhancement)

Manual Editing
--------------

Both config files are YAML and can be edited manually:

.. code-block:: bash

    # Edit user config
    vim ~/.prompt-engineer/config.yaml

    # Edit workspace config
    vim .prompt-engineer/workspace.yaml

After manual edits, refresh the UI to see changes.

Troubleshooting
---------------

**Config not loading**

* Check YAML syntax with ``yamllint config.yaml``
* Verify file permissions
* Check error messages in terminal

**Variables not interpolating**

* Verify variable names match ``{var_name}`` syntax
* Check file paths are relative to workspace root
* Ensure files exist and are readable

**API errors**

* Verify API key is correct
* Check base URL for local providers
* Test connectivity: ``curl <base_url>/models``
