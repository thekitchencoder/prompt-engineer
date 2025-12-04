prompts module
==============

.. automodule:: prompt_engineer.prompts
   :members:
   :undoc-members:
   :show-inheritance:

Module Overview
---------------

The prompts module handles all prompt file operations and variable interpolation:

* File discovery and listing
* Loading and saving prompt files
* Variable extraction and interpolation
* Validation of prompt templates

Key Functions
-------------

File Operations
~~~~~~~~~~~~~~~

.. autofunction:: prompt_engineer.prompts.list_prompt_files
.. autofunction:: prompt_engineer.prompts.load_prompt_file
.. autofunction:: prompt_engineer.prompts.save_prompt_file

Variable Handling
~~~~~~~~~~~~~~~~~

.. autofunction:: prompt_engineer.prompts.extract_variables
.. autofunction:: prompt_engineer.prompts.load_variable_value
.. autofunction:: prompt_engineer.prompts.interpolate_prompt
.. autofunction:: prompt_engineer.prompts.validate_prompt_variables

Usage Examples
--------------

Listing Prompt Files
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import prompts

    workspace = "/path/to/workspace"
    prompt_dir = "prompts"

    files = prompts.list_prompt_files(workspace, prompt_dir)
    print("Available prompts:")
    for file in files:
        print(f"  - {file}")

Loading and Saving
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import prompts

    # Load a prompt
    content = prompts.load_prompt_file(workspace, "prompts", "system.txt")
    print(content)

    # Modify and save
    new_content = "You are a helpful coding assistant."
    result = prompts.save_prompt_file(workspace, "prompts", "system.txt", new_content)
    print(result)  # ✅ Saved: system.txt

Variable Interpolation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import prompts

    template = "Analyze this code:\n{code}\n\nExplain {concept}."

    # Extract variables
    vars = prompts.extract_variables(template)
    print(f"Variables: {vars}")  # ['code', 'concept']

    # Set up variable config
    variables = {
        "code": {
            "type": "file",
            "path": "data/sample.py"
        },
        "concept": {
            "type": "value",
            "value": "recursion"
        }
    }

    # Interpolate
    interpolated, unmapped = prompts.interpolate_prompt(template, workspace, variables)
    print(interpolated)
    print(f"Unmapped: {unmapped}")  # []

Validation
~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import prompts

    template = "Analyze {code} for {bugs}."
    variables = {
        "code": {"type": "value", "value": "sample code"}
    }

    unmapped, missing = prompts.validate_prompt_variables(template, variables)
    if unmapped:
        print(f"Unmapped variables: {unmapped}")  # ['bugs']
