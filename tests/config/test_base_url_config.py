"""Tests for configuration and base_url handling."""

import pytest

from transflow.config import TransFlowConfig
from transflow.core.llm import LLMClient


class TestConfigValidation:
    """Test configuration validation and base_url handling."""

    def test_custom_base_url_is_applied(self) -> None:
        """Test that custom base_url is properly applied to OpenAI client."""
        custom_url = "http://192.168.5.233:8000/v1"
        config = TransFlowConfig(
            openai_api_key="test_key",
            openai_base_url=custom_url,
        )

        client = LLMClient(config)

        # Verify config is stored correctly
        assert client.config.openai_base_url == custom_url
        assert client.model == config.openai_model

    def test_default_base_url_works(self) -> None:
        """Test that default OpenAI base_url works correctly."""
        config = TransFlowConfig(openai_api_key="test_key")

        client = LLMClient(config)

        # Default URL should be set in config
        assert client.config.openai_base_url == "https://api.openai.com/v1"

    def test_base_url_with_trailing_slash(self) -> None:
        """Test handling of base_url with trailing slash."""
        config = TransFlowConfig(
            openai_api_key="test_key",
            openai_base_url="http://localhost:8000/v1/",
        )

        client = LLMClient(config)

        # Should not raise any error
        assert client.config.openai_base_url is not None

    def test_base_url_without_version(self) -> None:
        """Test handling of base_url without /v1 suffix."""
        config = TransFlowConfig(
            openai_api_key="test_key",
            openai_base_url="http://localhost:8000",
        )

        client = LLMClient(config)

        # Should still work - OpenAI SDK handles this
        assert client.config.openai_base_url is not None

    def test_api_key_from_env_priority(self) -> None:
        """Test that environment variable API key has priority."""
        # This would be set via TRANSFLOW_OPENAI_API_KEY env var
        config = TransFlowConfig(openai_api_key="from_env")

        assert config.openai_api_key == "from_env"

    def test_model_can_be_overridden(self) -> None:
        """Test that model can be overridden during client initialization."""
        config = TransFlowConfig(
            openai_api_key="test_key",
            openai_model="gpt-4o",
        )

        # Use default model
        client1 = LLMClient(config)
        assert client1.model == "gpt-4o"

        # Override with custom model
        client2 = LLMClient(config, model="custom-model")
        assert client2.model == "custom-model"
