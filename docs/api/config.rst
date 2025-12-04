config module
=============

.. automodule:: prompt_engineer.config
   :members:
   :undoc-members:
   :show-inheritance:

Module Overview
---------------

The config module handles configuration management at two levels:

1. **User-level**: Global settings stored in ``~/.prompt-engineer/config.yaml``
2. **Workspace-level**: Project-specific settings in ``${workspace}/.prompt-engineer/workspace.yaml``

Key Functions
-------------

Loading and Saving
~~~~~~~~~~~~~~~~~~

.. autofunction:: prompt_engineer.config.load_user_config
.. autofunction:: prompt_engineer.config.save_user_config
.. autofunction:: prompt_engineer.config.load_workspace_config
.. autofunction:: prompt_engineer.config.save_workspace_config

Default Configurations
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: prompt_engineer.config.get_default_user_config
.. autofunction:: prompt_engineer.config.get_default_workspace_config

Validation
~~~~~~~~~~

.. autofunction:: prompt_engineer.config.validate_user_config
.. autofunction:: prompt_engineer.config.validate_workspace_config

Path Helpers
~~~~~~~~~~~~

.. autofunction:: prompt_engineer.config.get_user_config_path
.. autofunction:: prompt_engineer.config.get_workspace_config_path

Usage Examples
--------------

Loading User Config
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import config

    # Load user config (creates default if not exists)
    user_cfg = config.load_user_config()
    print(f"Provider: {user_cfg['provider']}")
    print(f"Models: {user_cfg['models']}")

Saving Workspace Config
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import config

    workspace_cfg = {
        "paths": {
            "prompts": "prompts"
        },
        "variables": {
            "my_var": {
                "type": "file",
                "path": "data/sample.txt"
            }
        }
    }

    result = config.save_workspace_config("/path/to/workspace", workspace_cfg)
    print(result)  # ✅ Workspace config saved to ...

Validation Example
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import config

    user_cfg = config.load_user_config()
    errors = config.validate_user_config(user_cfg)

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Config is valid!")
