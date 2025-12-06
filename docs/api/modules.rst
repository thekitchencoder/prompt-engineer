.. _api:

API Reference
=============

This section provides detailed API documentation for all modules.

.. toctree::
   :maxdepth: 2

   config
   prompts
   llm
   app

Overview
--------

Prompt Engineer consists of four main modules:

* **config**: Configuration management (user and workspace)
* **prompts**: Prompt file operations and variable interpolation
* **llm**: LLM provider integration and API calls
* **app**: Gradio web interface

Quick Links
-----------

Configuration Module
~~~~~~~~~~~~~~~~~~~~

:func:`prompt_engineer.config.load_user_config`
    Load user-level configuration

:func:`prompt_engineer.config.save_user_config`
    Save user-level configuration

:func:`prompt_engineer.config.load_workspace_config`
    Load workspace-level configuration

:func:`prompt_engineer.config.save_workspace_config`
    Save workspace-level configuration

Prompts Module
~~~~~~~~~~~~~~

:func:`prompt_engineer.prompts.list_prompt_files`
    List all prompt files in workspace

:func:`prompt_engineer.prompts.load_prompt_file`
    Load content from a prompt file

:func:`prompt_engineer.prompts.save_prompt_file`
    Save content to a prompt file

:func:`prompt_engineer.prompts.interpolate_prompt`
    Interpolate variables into prompt template

LLM Module
~~~~~~~~~~

:func:`prompt_engineer.llm.initialize_client`
    Initialize OpenAI-compatible client

:func:`prompt_engineer.llm.fetch_available_models`
    Fetch available models from provider

:func:`prompt_engineer.llm.call_llm_api`
    Call LLM API with prompt and parameters
