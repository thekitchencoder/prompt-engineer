app module
==========

.. automodule:: prompt_engineer.app
   :members:
   :undoc-members:
   :show-inheritance:

Module Overview
---------------

The app module provides the Gradio web interface with four accordion sections:

1. **User Configuration**: Provider settings, API keys, model selection
2. **Workspace Configuration**: Prompt paths, variable mappings
3. **Prompt Editor**: Edit and preview prompts with variable interpolation
4. **LLM Interaction**: Test prompts with real LLM API calls

Key Components
--------------

UI Sections
~~~~~~~~~~~

The interface is organized into collapsible accordion sections, each handling a specific aspect of the workflow:

* **Section 1**: Global user settings (persisted across workspaces)
* **Section 2**: Workspace-specific configuration (per-project)
* **Section 3**: Prompt file editing and preview
* **Section 4**: LLM testing with request/response views

UI Functions
------------

The module exports several key UI functions:

.. autofunction:: prompt_engineer.app.create_ui
.. autofunction:: prompt_engineer.app.main

Internal Functions
~~~~~~~~~~~~~~~~~~

These functions are used internally by the UI:

* ``check_user_config_changes``: Detects changes in user config for save button state
* ``save_user_config_ui``: Saves user config and syncs UI controls
* ``prepare_request_ui``: Builds request payload for immediate display
* ``execute_request_ui``: Executes LLM API call asynchronously
* ``check_prompt_changes``: Detects changes in prompt editor
* ``refresh_all_ui``: Comprehensive refresh of all UI components

Design Patterns
---------------

Change Tracking
~~~~~~~~~~~~~~~

Save buttons use hidden state to track changes:

1. Store original values in ``gr.State``
2. Compare current vs original on input change
3. Enable/disable button based on diff
4. Update state after successful save

Two-Phase Execution
~~~~~~~~~~~~~~~~~~~

LLM interaction splits into two phases:

1. **Prepare**: Build and display request immediately
2. **Execute**: Make API call and display response

This provides instant feedback while preparing the request.

Configuration Sync
~~~~~~~~~~~~~~~~~~

User config changes automatically sync to LLM test section controls without page reload.

Running the Application
-----------------------

From Command Line
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Default workspace (current directory)
    prompt-engineer

    # Specific workspace
    prompt-engineer --workspace /path/to/project

    # Custom port
    prompt-engineer --port 8080

    # Help
    prompt-engineer --help

From Python
~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import app

    # Launch with default settings
    app.main()

    # Launch with custom workspace
    import sys
    sys.argv = ['app.py', '--workspace', '/path/to/project']
    app.main()

Development Mode
~~~~~~~~~~~~~~~~

For development with auto-reload:

.. code-block:: bash

    # Install in editable mode
    pip install -e .

    # Run directly
    python -m prompt_engineer.app

UI Customization
----------------

The Gradio interface can be customized by modifying the ``create_ui`` function:

.. code-block:: python

    def create_ui(workspace_root: str):
        \"\"\"Create and return the Gradio UI.\"\"\"

        with gr.Blocks() as ui:
            # Custom title
            gr.Markdown("# My Custom Prompt Engineer")

            # Add custom sections
            # ...

        return ui

Theme Configuration
~~~~~~~~~~~~~~~~~~~

Gradio 6 themes are passed to ``.launch()``:

.. code-block:: python

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        theme="default"  # or "soft", "monochrome", etc.
    )

Event Handlers
--------------

The UI uses several event handlers for interactivity:

* ``.change()``: Triggered when input value changes
* ``.click()``: Triggered when button is clicked
* ``.select()``: Triggered when dropdown selection changes
* ``.then()``: Chains actions sequentially

Example event chain:

.. code-block:: python

    save_btn.click(
        fn=save_function,
        inputs=[field1, field2],
        outputs=[status]
    ).then(
        fn=update_state,
        outputs=[original_state]
    ).then(
        fn=disable_button,
        outputs=[save_btn]
    )
