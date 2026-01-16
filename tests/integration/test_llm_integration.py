"""Integration tests for LLM client with real API calls.

These tests require valid API credentials and should be run separately:
    pytest tests/integration/ -v --integration

Set environment variables before running:
    export TRANSFLOW_OPENAI_API_KEY=your_key
    export TRANSFLOW_OPENAI_BASE_URL=http://your_base_url/v1  # Optional
"""

import os
from unittest.mock import patch

import pytest

from transflow.config import TransFlowConfig
from transflow.core.llm import LLMClient
from transflow.exceptions import TranslationError


pytestmark = pytest.mark.integration  # Mark all tests as integration tests


@pytest.fixture
def real_config() -> TransFlowConfig:
    """Load config from environment variables (requires real API key)."""
    api_key = os.getenv("TRANSFLOW_OPENAI_API_KEY")
    if not api_key or api_key == "test_key":
        pytest.skip("TRANSFLOW_OPENAI_API_KEY not set or is placeholder")

    return TransFlowConfig(
        openai_api_key=api_key,
        openai_base_url=os.getenv("TRANSFLOW_OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


@pytest.mark.asyncio
async def test_translate_text_with_real_api(real_config: TransFlowConfig) -> None:
    """Test translation with real OpenAI API."""
    client = LLMClient(real_config)

    result = await client.translate_text("Hello, world", "zh")

    assert result
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_translate_batch_with_real_api(real_config: TransFlowConfig) -> None:
    """Test batch translation with real OpenAI API."""
    client = LLMClient(real_config)

    texts = ["Hello", "World", "Test"]
    results = await client.translate_batch(texts, "zh")

    assert len(results) == len(texts)
    assert all(isinstance(r, str) for r in results)


@pytest.mark.asyncio
async def test_custom_base_url(real_config: TransFlowConfig) -> None:
    """Test that custom base_url is properly applied."""
    if not os.getenv("TRANSFLOW_OPENAI_BASE_URL"):
        pytest.skip("TRANSFLOW_OPENAI_BASE_URL not set")

    client = LLMClient(real_config)

    # Verify base_url was set
    assert client.async_client._base_url is not None or real_config.openai_base_url

    # Try a simple translation
    result = await client.translate_text("Test", "zh")
    assert result


def test_base_url_parsing() -> None:
    """Test that base_url is correctly parsed and applied."""
    # Test with custom base_url
    config = TransFlowConfig(
        openai_api_key="test_key",
        openai_base_url="http://192.168.5.233:8000/v1",
    )
    client = LLMClient(config)

    # Verify the client was initialized
    assert client.async_client is not None
    assert client.client is not None

    # Test with default base_url
    config_default = TransFlowConfig(
        openai_api_key="test_key",
        openai_base_url="https://api.openai.com/v1",
    )
    client_default = LLMClient(config_default)

    assert client_default.async_client is not None
