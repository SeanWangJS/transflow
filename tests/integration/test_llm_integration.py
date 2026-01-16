"""Integration tests for LLM client with real API calls.

These tests validate real API compatibility and require:
1. Valid API credentials (TRANSFLOW_OPENAI_API_KEY)
2. Optional custom base URL (TRANSFLOW_OPENAI_BASE_URL)

Environment consistency guarantees:
    - Tests use isolated client instances (no shared state)
    - Each test gets fresh config from environment
    - Tests skip gracefully if credentials not available
    - No credentials logged or printed
    - Environment variables never modified by tests

Running integration tests:
    # With environment variables
    export TRANSFLOW_OPENAI_API_KEY=sk_test_xxx
    export TRANSFLOW_OPENAI_BASE_URL=http://localhost:8000/v1
    pytest tests/integration/ -v -m integration

    # Or with .env.test file (not committed to git)
    pytest tests/integration/ -v -m integration
"""

import os

import pytest

from transflow.config import TransFlowConfig
from transflow.core.llm import LLMClient


pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def integration_config() -> TransFlowConfig:
    """Load and validate integration test configuration.
    
    Scope: function - Fresh config for each test
    
    Returns:
        TransFlowConfig with real API credentials
        
    Raises:
        pytest.skip if credentials not properly configured
    """
    api_key = os.getenv("TRANSFLOW_OPENAI_API_KEY", "").strip()
    base_url = os.getenv("TRANSFLOW_OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    
    # Validate credentials
    if not api_key or api_key in ("test_key", "sk_test_", ""):
        pytest.skip(
            "Integration tests require valid TRANSFLOW_OPENAI_API_KEY. "
            "Set environment variable: export TRANSFLOW_OPENAI_API_KEY=<your_key>"
        )
    
    return TransFlowConfig(
        openai_api_key=api_key,
        openai_base_url=base_url,
    )


@pytest.fixture(scope="function")
def isolated_client(integration_config: TransFlowConfig) -> LLMClient:
    """Create an isolated LLM client for testing.
    
    Scope: function - New client for each test, ensuring isolation
    
    Returns:
        Fresh LLMClient instance
    """
    return LLMClient(integration_config)


@pytest.mark.asyncio
async def test_api_connectivity(isolated_client: LLMClient) -> None:
    """Verify API endpoint is reachable and responding."""
    result = await isolated_client.translate_text("test", "zh")
    
    assert result is not None
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_translate_text_with_real_api(isolated_client: LLMClient) -> None:
    """Test single text translation with real API."""
    result = await isolated_client.translate_text("Hello, world", "zh")

    assert result
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_translate_batch_with_real_api(isolated_client: LLMClient) -> None:
    """Test batch translation with real API."""
    texts = ["Hello", "World", "Test"]
    results = await isolated_client.translate_batch(texts, "zh")

    assert len(results) == len(texts)
    assert all(isinstance(r, str) for r in results)


@pytest.mark.asyncio
async def test_custom_base_url(integration_config: TransFlowConfig) -> None:
    """Test that custom base_url is properly applied and working."""
    base_url = os.getenv("TRANSFLOW_OPENAI_BASE_URL")
    
    if base_url and base_url != "https://api.openai.com/v1":
        # Only test if custom base_url is configured
        client = LLMClient(integration_config)
        result = await client.translate_text("test", "zh")
        assert result is not None


@pytest.mark.asyncio
async def test_auto_language_detection(isolated_client: LLMClient) -> None:
    """Test automatic language detection."""
    # English text with auto detection
    result_en = await isolated_client.translate_text(
        "The quick brown fox",
        target_language="zh",
        source_language="auto"
    )
    assert result_en is not None
    assert isinstance(result_en, str)


@pytest.mark.asyncio
async def test_empty_text_handling(isolated_client: LLMClient) -> None:
    """Test that empty text is handled correctly without API calls."""
    result = await isolated_client.translate_text("", "zh")
    assert result == ""
    
    result_spaces = await isolated_client.translate_text("   ", "zh")
    assert result_spaces.strip() == ""


@pytest.mark.asyncio
async def test_environment_isolation(integration_config: TransFlowConfig) -> None:
    """Verify that test environment doesn't leak between tests.
    
    This ensures:
    - Each test uses fresh config
    - No shared state across tests
    - Credentials are isolated
    """
    api_key = integration_config.openai_api_key
    assert api_key is not None
    assert len(api_key) > 0
    
    # Create two independent clients
    client1 = LLMClient(integration_config)
    client2 = LLMClient(integration_config)
    
    # Verify they are independent instances
    assert client1 is not client2
    assert client1.config.openai_api_key == client2.config.openai_api_key
    assert client1.async_client is not client2.async_client

