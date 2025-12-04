"""Unit tests for llm.py."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from prompt_engineer import llm


class TestInitializeClient:
    """Tests for client initialization."""

    @patch('prompt_engineer.llm.OpenAI')
    def test_initialize_with_api_key_only(self, mock_openai):
        """Test initializing client with API key only."""
        llm.initialize_client("test-key")

        mock_openai.assert_called_once_with(api_key="test-key")

    @patch('prompt_engineer.llm.OpenAI')
    def test_initialize_with_base_url(self, mock_openai):
        """Test initializing client with custom base URL."""
        llm.initialize_client("test-key", "http://localhost:8000/v1")

        mock_openai.assert_called_once_with(
            api_key="test-key",
            base_url="http://localhost:8000/v1"
        )

    @patch('prompt_engineer.llm.OpenAI')
    def test_initialize_with_base_url_no_key(self, mock_openai):
        """Test initializing client with base URL and no key uses 'not-needed'."""
        llm.initialize_client("", "http://localhost:8000/v1")

        mock_openai.assert_called_once_with(
            api_key="not-needed",
            base_url="http://localhost:8000/v1"
        )


class TestFetchAvailableModels:
    """Tests for fetching available models."""

    @patch('prompt_engineer.llm.initialize_client')
    def test_fetch_models_success(self, mock_init):
        """Test successfully fetching models."""
        # Mock client and response
        mock_client = Mock()
        mock_init.return_value = mock_client

        mock_model1 = Mock()
        mock_model1.id = "gpt-4o"
        mock_model2 = Mock()
        mock_model2.id = "gpt-3.5-turbo"

        mock_response = Mock()
        mock_response.data = [mock_model1, mock_model2]
        mock_client.models.list.return_value = mock_response

        # Test
        success, result = llm.fetch_available_models("test-key")

        assert success is True
        assert result == ["gpt-3.5-turbo", "gpt-4o"]  # Sorted

    @patch('prompt_engineer.llm.initialize_client')
    def test_fetch_models_no_models(self, mock_init):
        """Test fetching models when none are available."""
        mock_client = Mock()
        mock_init.return_value = mock_client

        mock_response = Mock()
        mock_response.data = []
        mock_client.models.list.return_value = mock_response

        success, result = llm.fetch_available_models("test-key")

        assert success is False
        assert "no models found" in result.lower()

    @patch('prompt_engineer.llm.initialize_client')
    def test_fetch_models_connection_error(self, mock_init):
        """Test handling connection errors."""
        mock_client = Mock()
        mock_init.return_value = mock_client
        mock_client.models.list.side_effect = Exception("Connection refused")

        success, result = llm.fetch_available_models("test-key", "http://localhost:8000")

        assert success is False
        assert "connection" in result.lower()

    @patch('prompt_engineer.llm.initialize_client')
    def test_fetch_models_auth_error(self, mock_init):
        """Test handling authentication errors."""
        mock_client = Mock()
        mock_init.return_value = mock_client
        mock_client.models.list.side_effect = Exception("401 Unauthorized")

        success, result = llm.fetch_available_models("bad-key")

        assert success is False
        assert "authentication" in result.lower() or "invalid" in result.lower()

    @patch('prompt_engineer.llm.initialize_client')
    def test_fetch_models_forbidden_error(self, mock_init):
        """Test handling forbidden errors."""
        mock_client = Mock()
        mock_init.return_value = mock_client
        mock_client.models.list.side_effect = Exception("403 Forbidden")

        success, result = llm.fetch_available_models("test-key")

        assert success is False
        assert "forbidden" in result.lower() or "permission" in result.lower()


class TestProcessThinkingResponse:
    """Tests for processing thinking tags in responses."""

    def test_no_thinking_tags(self):
        """Test processing response without thinking tags."""
        content = "This is a normal response."
        result = llm.process_thinking_response(content)

        assert result == content

    def test_single_thinking_tag(self):
        """Test processing response with single thinking tag."""
        content = "<think>Let me analyze this...</think>Here is my answer."
        result = llm.process_thinking_response(content)

        assert "🤔 Thinking" in result
        assert "Let me analyze this..." in result
        assert "Here is my answer" in result

    def test_multiple_thinking_tags(self):
        """Test processing response with multiple thinking tags."""
        content = "<think>First thought</think>Some text<think>Second thought</think>Final answer."
        result = llm.process_thinking_response(content)

        assert "🤔 Thinking (1)" in result
        assert "🤔 Thinking (2)" in result
        assert "First thought" in result
        assert "Second thought" in result
        assert "Final answer" in result

    def test_thinking_only_no_response(self):
        """Test processing when only thinking tags exist."""
        content = "<think>Just thinking, no answer</think>"
        result = llm.process_thinking_response(content)

        assert "🤔 Thinking" in result
        assert "Just thinking, no answer" in result

    def test_thinking_with_newlines(self):
        """Test processing thinking tags with newlines."""
        content = """<think>
        Line 1 of thinking
        Line 2 of thinking
        </think>
        Response text here."""

        result = llm.process_thinking_response(content)

        assert "🤔 Thinking" in result
        assert "Line 1 of thinking" in result
        assert "Response text here" in result


class TestCallLLMAPI:
    """Tests for calling LLM API."""

    @patch('prompt_engineer.llm.initialize_client')
    def test_call_api_success(self, mock_init):
        """Test successful API call."""
        # Mock client and response
        mock_client = Mock()
        mock_init.return_value = mock_client

        mock_message = Mock()
        mock_message.content = "Test response content"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model_dump.return_value = {
            "id": "test-id",
            "model": "gpt-4o",
            "choices": [{"message": {"content": "Test response content"}}]
        }

        mock_client.chat.completions.create.return_value = mock_response

        # Test
        messages = [{"role": "user", "content": "Test prompt"}]
        formatted, request, response = llm.call_llm_api(
            api_key="test-key",
            base_url=None,
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        assert formatted == "Test response content"
        assert request["model"] == "gpt-4o"
        assert request["messages"] == messages
        assert request["temperature"] == 0.7
        assert request["max_tokens"] == 2000
        assert "id" in response

    @patch('prompt_engineer.llm.initialize_client')
    def test_call_api_with_thinking_tags(self, mock_init):
        """Test API call that returns thinking tags."""
        mock_client = Mock()
        mock_init.return_value = mock_client

        mock_message = Mock()
        mock_message.content = "<think>Analyzing...</think>The answer is 42."

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model_dump.return_value = {"id": "test"}

        mock_client.chat.completions.create.return_value = mock_response

        # Test
        messages = [{"role": "user", "content": "What is the answer?"}]
        formatted, request, response = llm.call_llm_api(
            api_key="test-key",
            base_url=None,
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        assert "🤔 Thinking" in formatted
        assert "Analyzing..." in formatted
        assert "The answer is 42" in formatted

    @patch('prompt_engineer.llm.initialize_client')
    def test_call_api_error(self, mock_init):
        """Test handling API call errors."""
        mock_client = Mock()
        mock_init.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        # Test
        messages = [{"role": "user", "content": "Test"}]
        formatted, request, response = llm.call_llm_api(
            api_key="test-key",
            base_url=None,
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        assert "Error" in formatted
        assert "error" in response


class TestTokenEstimation:
    """Tests for token estimation."""

    def test_estimate_tokens_empty(self):
        """Test estimating tokens for empty string."""
        assert llm.estimate_tokens("") == 0

    def test_estimate_tokens_short(self):
        """Test estimating tokens for short text."""
        # "Hello world" = 11 chars ÷ 4 = 2.75 → 2 tokens
        assert llm.estimate_tokens("Hello world") == 2

    def test_estimate_tokens_long(self):
        """Test estimating tokens for longer text."""
        text = "a" * 400  # 400 chars ÷ 4 = 100 tokens
        assert llm.estimate_tokens(text) == 100


class TestCostEstimation:
    """Tests for cost estimation."""

    def test_estimate_cost_gpt4o(self):
        """Test cost estimation for GPT-4o."""
        cost = llm.estimate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)

        # 1000/1000 * 0.0025 + 500/1000 * 0.01 = 0.0025 + 0.005 = 0.0075
        assert cost == "$0.0075"

    def test_estimate_cost_gpt4o_mini(self):
        """Test cost estimation for GPT-4o-mini."""
        cost = llm.estimate_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)

        # 1000/1000 * 0.00015 + 500/1000 * 0.0006 = 0.00015 + 0.0003 = 0.00045
        assert cost == "$0.0005"  # Rounded

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation for unknown model."""
        cost = llm.estimate_cost("unknown-model", prompt_tokens=1000, completion_tokens=500)

        assert cost == "Unknown"

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        cost = llm.estimate_cost("gpt-4o", prompt_tokens=0, completion_tokens=0)

        assert cost == "$0.0000"
