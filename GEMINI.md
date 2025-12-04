# Project Overview

This project, "Prompt Engineer," is a CLI-based developer workbench for rapid AI prompt engineering iteration. It's built with Python and uses the Gradio library to create a web-based UI. The main goal is to provide a low-friction workflow for editing and testing prompt templates that are part of an application's source code.

**Key Technologies:**

*   **Backend:** Python
*   **UI:** Gradio
*   **Configuration:** YAML
*   **Packaging:** `pip` and `setuptools` (inferred from `pyproject.toml` and `requirements.txt`)

**Architecture:**

The application is structured into several modules:

*   `app.py`: The main entry point, containing the Gradio UI and event handling logic.
*   `config.py`: Manages user and workspace configurations, including loading, saving, and validation.
*   `prompts.py`: Handles prompt file operations, variable extraction, and interpolation.
*   `llm.py`: Interacts with LLM providers, fetches available models, and makes API calls.

The application operates on a "workspace" concept, which is the directory where the user's project resides. It reads and writes prompt files directly within the user's project.

# Building and Running

**1. Installation:**

To install the necessary dependencies, run the following command in your terminal:

```bash
pip install -r requirements.txt
```

To install the application in editable mode (for development):

```bash
pip install -e .
```

**2. Running the Application:**

You can run the application using the following command:

```bash
prompt-engineer
```

Or by directly running the `app.py` module:

```bash
python -m prompt_engineer.app
```

You can also specify a workspace directory and a port:

```bash
prompt-engineer --workspace /path/to/your/project --port 8080
```

**3. Running with Docker:**

The project includes a `Dockerfile` and `docker-compose.yml` for running the application in a container.

To build the Docker image:

```bash
docker build -t prompt-engineer .
```

To run with `docker-compose`:

```bash
docker-compose up
```

# Development Conventions

*   **Configuration:** The application uses a two-tiered configuration system:
    *   **User Configuration:** Stored in `~/.prompt-engineer/config.yaml`, this file contains global settings like API keys and provider presets.
    *   **Workspace Configuration:** Stored in `.prompt-engineer/workspace.yaml` within the project directory, this file defines workspace-specific settings like the location of prompt files and variable mappings.
*   **Prompts:** Prompt templates are expected to be text files and can contain variables in the format `{variable_name}`.
*   **Variables:** Variables can be of two types: `file` (the value is read from a file) or `value` (the value is a literal string).
*   **LLM Interaction:** The application is designed to be provider-agnostic and works with any OpenAI-compatible API.
*   **UI:** The UI is built with Gradio and is organized into collapsible sections for configuration, editing, and testing.
