# Prompt Engineer Documentation

This directory contains the Sphinx documentation for Prompt Engineer.

## Building the Documentation

### Prerequisites

Install documentation dependencies:

```bash
pip install -e ".[docs]"
```

Or install manually:

```bash
pip install sphinx sphinx_rtd_theme
```

### Build HTML Documentation

```bash
cd docs
make html
```

The generated HTML will be in `_build/html/`. Open `_build/html/index.html` in your browser.

### Build Other Formats

```bash
# PDF (requires LaTeX)
make latexpdf

# ePub
make epub

# Plain text
make text

# Man pages
make man
```

### Clean Build Files

```bash
make clean
```

## Documentation Structure

```
docs/
├── conf.py                 # Sphinx configuration
├── index.rst              # Main documentation page
├── installation.rst       # Installation guide
├── quickstart.rst         # Quick start tutorial
├── architecture.rst       # Architecture overview
├── configuration.rst      # Configuration reference
├── api/                   # API documentation
│   ├── modules.rst        # API index
│   ├── config.rst         # config.py API
│   ├── prompts.rst        # prompts.py API
│   ├── llm.rst           # llm.py API
│   └── app.rst           # app.py API
├── _static/              # Static files (CSS, images)
└── _templates/           # Custom templates
```

## Writing Documentation

### ReStructuredText (RST) Basics

```rst
Section Title
=============

Subsection
----------

**bold text**
*italic text*
``code``

- Bullet point
- Another point

1. Numbered item
2. Another item

.. code-block:: python

   def example():
       print("Code example")

:ref:`link-to-label`
```

### Adding New Pages

1. Create a new `.rst` file in `docs/`
2. Add it to the `toctree` in `index.rst` or relevant parent page
3. Build to verify

### API Documentation

API docs are auto-generated from docstrings using Sphinx autodoc. To document a new module:

1. Create `docs/api/module_name.rst`
2. Add `.. automodule:: prompt_engineer.module_name`
3. Add to `api/modules.rst` toctree

## Deployment

### GitHub Pages

Set up automatic deployment:

1. Build docs: `make html`
2. Copy `_build/html/*` to `gh-pages` branch
3. Push to GitHub

### Read the Docs

1. Connect repository to https://readthedocs.org
2. Configure build settings
3. Docs will auto-build on push

## Troubleshooting

**Module import errors during build:**
- Ensure source code is in Python path
- Check `sys.path` in `conf.py`
- Install the package: `pip install -e .`

**Theme not found:**
- Install theme: `pip install sphinx_rtd_theme`

**Broken references:**
- Check label names match
- Verify file paths in toctree
- Use `make linkcheck` to find broken links
