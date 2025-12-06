.. _quickstart:

Quick Start Guide
=================

This guide will help you get started with Prompt Engineer in under 5 minutes.

1. Create a Workspace
---------------------

Create a new directory for your prompts::

    mkdir -p my-project/prompts
    mkdir -p my-project/prompt-data
    cd my-project

2. Create Your First Prompt
----------------------------

Create a simple prompt file::

    echo "Analyze the following code:\n{code}" > prompts/analyze.txt

3. Launch Prompt Engineer
--------------------------

Start the application::

    prompt-engineer --workspace .

This will open a web interface at http://localhost:7860

4. Configure User Settings
---------------------------

In the **User Configuration** section:

1. Select your provider (e.g., "openai", "ollama")
2. Enter your API key (if required)
3. Load available models
4. Select a default model
5. Click "Save User Config"

5. Configure Workspace Variables
---------------------------------

In the **Workspace Configuration** section:

1. Set prompts directory path (default: "prompts")
2. Add variables:

   * Variable name: ``code``
   * Type: ``file``
   * Path: ``prompt-data/sample.py``

3. Click "Save Workspace Config"

6. Edit and Test Prompts
-------------------------

In the **Prompt Editor** section:

1. Select your prompt file from the dropdown
2. Edit the prompt template
3. View interpolated preview in the Preview tab
4. Save changes

In the **LLM Interaction** section:

1. Select your prompt
2. Adjust temperature and max_tokens if needed
3. Click "Prepare & Execute Request"
4. View the response in the Output tab

Workflow Tips
-------------

**Variable Types**

* **file**: Load content from a file (relative to workspace root)
* **value**: Inline text value stored in config

**Prompt Organization**

* Root-level prompts for main templates
* Nested folders for organized templates
* Any file extension supported

**Testing Workflow**

1. Edit prompt in source code
2. Refresh in Prompt Engineer
3. Test with different variables
4. Iterate based on results

Next Steps
----------

Learn more about:

* :ref:`architecture` - Understanding the modular design
* :ref:`configuration` - Advanced configuration options
* :ref:`api` - API reference for developers
