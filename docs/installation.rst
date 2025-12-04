.. _installation:

Installation
============

Requirements
------------

* Python 3.8 or higher
* pip or uv for package management

From Source
-----------

1. Clone the repository::

    git clone https://github.com/thekitchencoder/prompt-engineer.git
    cd prompt-engineer

2. Create and activate a virtual environment::

    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate

3. Install in development mode::

    pip install -e .

Verification
------------

Verify the installation by running::

    prompt-engineer --help

You should see the command-line interface help message.

Dependencies
------------

Core dependencies:

* **gradio**: Web UI framework
* **pyyaml**: Configuration file handling
* **openai**: LLM API client (OpenAI-compatible)

Development dependencies:

* **pytest**: Testing framework
* **sphinx**: Documentation generator
* **sphinx_rtd_theme**: ReadTheDocs theme for Sphinx

Next Steps
----------

After installation, proceed to the :ref:`quickstart` guide.
