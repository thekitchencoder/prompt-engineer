llm module
==========

.. automodule:: prompt_engineer.llm
   :members:
   :undoc-members:
   :show-inheritance:

Module Overview
---------------

The llm module provides integration with LLM providers via OpenAI-compatible APIs:

* Client initialization
* Model discovery
* API calls with error handling
* Response processing (including thinking tags)
* Token and cost estimation

Key Functions
-------------

Client Management
~~~~~~~~~~~~~~~~~

.. autofunction:: prompt_engineer.llm.initialize_client
.. autofunction:: prompt_engineer.llm.fetch_available_models

API Calls
~~~~~~~~~

.. autofunction:: prompt_engineer.llm.call_llm_api

Response Processing
~~~~~~~~~~~~~~~~~~~

.. autofunction:: prompt_engineer.llm.process_thinking_response

Analytics
~~~~~~~~~

.. autofunction:: prompt_engineer.llm.estimate_tokens
.. autofunction:: prompt_engineer.llm.estimate_cost

Usage Examples
--------------

Fetching Available Models
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import llm

    # For OpenAI
    success, models = llm.fetch_available_models(
        api_key="sk-...",
        base_url=None
    )

    if success:
        print(f"Available models: {models}")
    else:
        print(f"Error: {models}")

    # For local Ollama
    success, models = llm.fetch_available_models(
        api_key="",
        base_url="http://localhost:11434/v1"
    )

Making API Calls
~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import llm

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Python?"}
    ]

    formatted, request, response = llm.call_llm_api(
        api_key="sk-...",
        base_url=None,
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=2000
    )

    print("Response:")
    print(formatted)

    print("\nRequest payload:")
    print(request)

    print("\nFull response:")
    print(response)

Processing Thinking Tags
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import llm

    # Response from a reasoning model
    raw_response = """
    <think>
    Let me break this down:
    1. First consideration...
    2. Second consideration...
    </think>
    The answer is 42 because of the following reasons...
    """

    formatted = llm.process_thinking_response(raw_response)
    print(formatted)
    # Output:
    # 🤔 Thinking (1):
    # ```
    # Let me break this down:
    # 1. First consideration...
    # 2. Second consideration...
    # ```
    # ---
    # The answer is 42 because of the following reasons...

Token and Cost Estimation
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from prompt_engineer import llm

    text = "This is a sample prompt text..."
    tokens = llm.estimate_tokens(text)
    print(f"Estimated tokens: {tokens}")

    cost = llm.estimate_cost(
        model="gpt-4o",
        prompt_tokens=1000,
        completion_tokens=500
    )
    print(f"Estimated cost: {cost}")  # $0.0075

Error Handling
--------------

The module provides robust error handling:

.. code-block:: python

    from prompt_engineer import llm

    success, result = llm.fetch_available_models(
        api_key="invalid-key",
        base_url=None
    )

    if not success:
        print(f"Error: {result}")
        # Error: Authentication failed: Invalid API key

Supported errors:

* Connection errors (unreachable endpoint)
* Authentication errors (invalid API key)
* Authorization errors (insufficient permissions)
* General API errors (rate limits, etc.)
