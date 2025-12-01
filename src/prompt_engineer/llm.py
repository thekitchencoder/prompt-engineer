"""LLM provider integration and API calls."""

import re
from openai import OpenAI
from typing import Dict, Any, Tuple, Optional, List


def initialize_client(api_key: str, base_url: Optional[str] = None) -> OpenAI:
    """Initialize OpenAI-compatible client."""
    if base_url:
        return OpenAI(api_key=api_key or "not-needed", base_url=base_url)
    else:
        return OpenAI(api_key=api_key)


def fetch_available_models(api_key: str, base_url: Optional[str] = None) -> Tuple[bool, Any]:
    """
    Fetch available models from provider API.

    Returns:
        (success: bool, result: list of models or error message)
    """
    try:
        client = initialize_client(api_key, base_url)
        models_response = client.models.list()
        model_ids = [model.id for model in models_response.data]

        if not model_ids:
            return False, "No models found at the specified endpoint"

        model_ids.sort()
        return True, model_ids

    except Exception as e:
        error_msg = str(e)
        if "Connection" in error_msg or "connect" in error_msg.lower():
            return False, f"Connection failed: Unable to reach {base_url or 'OpenAI API'}"
        elif "401" in error_msg or "Unauthorized" in error_msg:
            return False, "Authentication failed: Invalid API key"
        elif "403" in error_msg or "Forbidden" in error_msg:
            return False, "Access forbidden: Check API key permissions"
        else:
            return False, f"Error fetching models: {error_msg}"


def process_thinking_response(content: str) -> str:
    """
    Process response content to handle thinking tags from reasoning models.
    Extracts <think>...</think> sections and formats them for display.
    """
    # Check if response contains thinking tags
    think_pattern = r'<think>(.*?)</think>'
    thinks = re.findall(think_pattern, content, re.DOTALL)

    if not thinks:
        # No thinking tags, return as-is
        return content

    # Remove thinking tags from content
    response_without_think = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()

    # Format thinking sections
    formatted_thinks = []
    for i, think in enumerate(thinks, 1):
        think_text = think.strip()
        formatted_thinks.append(f"**🤔 Thinking ({i}):**\n```\n{think_text}\n```\n")

    # Combine: thinking sections first, then response
    if formatted_thinks:
        thinking_section = "\n".join(formatted_thinks)
        if response_without_think:
            return f"{thinking_section}\n---\n\n{response_without_think}"
        else:
            return thinking_section

    return response_without_think if response_without_think else content


def call_llm_api(
    api_key: str,
    base_url: Optional[str],
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Call LLM API and return formatted response, raw request, and raw response.

    Returns:
        (formatted_content, raw_request, raw_response)
    """
    try:
        client = initialize_client(api_key, base_url)

        # Build request payload
        request_payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Make API call
        response = client.chat.completions.create(**request_payload)

        # Extract formatted content
        raw_content = response.choices[0].message.content

        # Process thinking tags
        formatted_content = process_thinking_response(raw_content)

        # Convert to dict for display
        raw_response = response.model_dump()

        return formatted_content, request_payload, raw_response

    except Exception as e:
        error_msg = f"Error calling LLM API: {e}"
        return error_msg, {}, {"error": str(e)}


def estimate_tokens(text: str) -> int:
    """Rough estimate of tokens (4 chars ≈ 1 token)."""
    return len(text) // 4


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> str:
    """Estimate cost based on model pricing."""
    # Pricing per 1K tokens (input, output)
    PRICING = {
        "gpt-4o": (0.0025, 0.01),
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-3.5-turbo": (0.0005, 0.0015),
    }

    # Default pricing if model not found
    prices = PRICING.get(model, (0.0, 0.0))

    if prices == (0.0, 0.0):
        return "Unknown"

    cost = (prompt_tokens / 1000 * prices[0]) + (completion_tokens / 1000 * prices[1])
    return f"${cost:.4f}"
