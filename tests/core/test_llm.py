"""Tests for LLM client.

Following Google Python testing guidelines.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from transflow.config import TransFlowConfig
from transflow.core.llm import LLMClient
from transflow.exceptions import APIError, TranslationError


class TestLLMClient:
    """Tests for LLMClient class."""

    def test_init_without_api_key_raises_error(self) -> None:
        """Test LLM client initialization fails when API key is missing."""
        # Arrange
        config = TransFlowConfig(openai_api_key=None)

        # Act & Assert
        with pytest.raises(APIError, match="OpenAI API key is required"):
            LLMClient(config)

    def test_init_with_valid_config(self) -> None:
        """Test LLM client initializes successfully with valid configuration."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")

        # Act
        client = LLMClient(config)

        # Assert
        assert client.config == config
        assert client.model == config.openai_model
        assert client.http_client is not None

    def test_init_with_custom_model(self) -> None:
        """Test LLM client accepts custom model override."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        custom_model = "gpt-4-turbo"

        # Act
        client = LLMClient(config, model=custom_model)

        # Assert
        assert client.model == custom_model

    @pytest.mark.asyncio
    async def test_translate_text_success(self) -> None:
        """Test successful text translation returns translated content."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "你好，世界"}}]
        }

        # Act
        with patch.object(
            client.http_client,
            "post",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await client.translate_text("Hello, world", "zh")

        # Assert
        assert result == "你好，世界"

    @pytest.mark.asyncio
    async def test_translate_text_empty_input_returns_empty(self) -> None:
        """Test translation of empty text returns empty string without API call."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        mock_post = AsyncMock()

        # Act
        with patch.object(client.http_client, "post", new=mock_post):
            result = await client.translate_text("  ", "zh")

        # Assert
        assert result == "  "
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_translate_text_api_error_raises_translation_error(self) -> None:
        """Test translation raises TranslationError on API failure."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        # Act & Assert
        with patch.object(
            client.http_client,
            "post",
            new=AsyncMock(side_effect=Exception("API error")),
        ):
            with pytest.raises(TranslationError, match="Failed to translate text"):
                await client.translate_text("Hello", "zh")

    @pytest.mark.asyncio
    async def test_translate_batch_success(self) -> None:
        """Test successful batch translation returns list of translations."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "你好\n\n---SPLIT---\n\n世界"
                    }
                }
            ]
        }

        # Act
        with patch.object(
            client.http_client,
            "post",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await client.translate_batch(["Hello", "World"], "zh")

        # Assert
        assert len(result) == 2
        assert result[0] == "你好"
        assert result[1] == "世界"

    @pytest.mark.asyncio
    async def test_translate_batch_empty_list_returns_empty(self) -> None:
        """Test batch translation of empty list returns empty list."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        # Act
        result = await client.translate_batch([], "zh")

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_translate_batch_preserves_empty_strings(self) -> None:
        """Test batch translation preserves empty strings in correct positions."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "你好"}}]
        }

        # Act
        with patch.object(
            client.http_client,
            "post",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await client.translate_batch(["Hello", "", ""], "zh")

        # Assert
        assert len(result) == 3
        assert result[0] == "你好"
        assert result[1] == ""
        assert result[2] == ""

    @pytest.mark.asyncio
    async def test_translate_batch_fallback_on_split_mismatch(self) -> None:
        """Test batch translation falls back to individual translation on split error."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        # First call (batch) returns mismatched splits
        mock_batch_response = MagicMock()
        mock_batch_response.json.return_value = {
            "choices": [{"message": {"content": "你好"}}]  # Only 1 instead of 2
        }

        # Individual calls return correct translations
        mock_individual_responses = [
            MagicMock(json=lambda: {"choices": [{"message": {"content": "你好"}}]}),
            MagicMock(json=lambda: {"choices": [{"message": {"content": "世界"}}]}),
        ]

        call_count = [0]

        async def mock_post(*args, **kwargs):
            if call_count[0] == 0:
                call_count[0] += 1
                return mock_batch_response
            else:
                idx = call_count[0] - 1
                call_count[0] += 1
                return mock_individual_responses[idx]

        # Act
        with patch.object(client.http_client, "post", new=AsyncMock(side_effect=mock_post)):
            result = await client.translate_batch(["Hello", "World"], "zh")

        # Assert
        assert len(result) == 2

    def test_estimate_tokens_returns_reasonable_estimate(self) -> None:
        """Test token estimation returns plausible value."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)
        text = "Hello, world! " * 10  # ~130 characters

        # Act
        tokens = client.estimate_tokens(text)

        # Assert
        assert tokens > 0
        assert tokens < len(text)  # Tokens should be less than character count

    def test_build_translation_prompt_auto_language(self) -> None:
        """Test translation prompt generation with auto language detection."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        # Act
        prompt = client._build_translation_prompt("Hello", "zh", "auto")

        # Assert
        assert "Chinese" in prompt
        assert "Hello" in prompt
        assert "Translate" in prompt

    def test_build_translation_prompt_specific_languages(self) -> None:
        """Test translation prompt generation with specific source and target languages."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        client = LLMClient(config)

        # Act
        prompt = client._build_translation_prompt("Hello", "zh", "en")

        # Assert
        assert "English" in prompt
        assert "Chinese" in prompt
        assert "Hello" in prompt
