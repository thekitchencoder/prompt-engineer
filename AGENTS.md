# Repository Guidelines

## Project Structure & Module Organization
Source lives under `src/prompt_engineer`, with UI logic in `app.py`, configuration helpers in `config.py`, LLM adapters in `llm.py`, and prompt utilities in `prompts.py`. Example workspaces and provider notes sit in `examples/`, `CLAUDE.md`, and `GEMINI.md`. Docker assets (`Dockerfile`, `docker-compose.yml`, `DOCKER.md`) support containerized workflows, while `requirements.txt`, `pyproject.toml`, and `uv.lock` define Python dependencies. Create new experiment modules inside `src/prompt_engineer/` and mirror them with tests under `tests/` (add the folder if missing).

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: standard development environment.
- `pip install -e .` (or `uv sync && uv run prompt-engineer`): install editable dependencies.
- `prompt-engineer --workspace <path>`: run the Gradio UI against a target workspace.
- `python -m prompt_engineer.app`: direct module execution; helpful for debugging import paths.
- `docker-compose up`: builds and runs the bundled image for parity checks.

## Coding Style & Naming Conventions
Use Python 3.9+ with 4-space indentation, type hints, and module-level docstrings (see `app.py`). Favor snake_case for functions/modules, PascalCase for UI component wrappers, and keep prompt IDs descriptive (e.g., `system_reviewer.txt`). Maintain cohesive helper modules instead of sprawling scripts, and keep provider-specific logic inside `llm.py` so UI layers stay declarative.

## Testing Guidelines
Pytest is the expected harness; place suites next to the features they cover (e.g., `tests/test_prompts.py`). Name tests after observable behavior (`test_extract_variables_handles_nested_braces`). Fast-running unit tests are preferred, but add integration cases that exercise `prompt-engineer` CLI flows by stubbing network calls. Run `pytest` before every PR and include regression tests with each fix.

## Commit & Pull Request Guidelines
Follow the existing conventional style from `git log` (`feat:`, `fix:`, `docs:`). Keep commits scoped to a single concern and include brief reasoning in the body when behavior changes. PRs should describe the user-facing impact, list validation steps (`pytest`, manual CLI checks), and link relevant issues. Include screenshots or terminal captures when UI output changes, and ensure configuration files or sample prompts stay synchronized.

## Security & Configuration Tips
Never commit API keys or workspace data; the UI already persists credentials in `~/.prompt-engineer/config.yaml`. When documenting new providers, mask secrets and describe required environment variables instead. For sample prompts, strip customer data and prefer files under `examples/` so contributors can test safely.
