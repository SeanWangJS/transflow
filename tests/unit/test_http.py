"""Tests for HTTP client utilities.

Following Google Python testing guidelines:
- Test function names clearly describe what is being tested
- Use Arrange-Act-Assert pattern
- Each test validates one specific behavior
- Use docstrings to explain test purpose
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from transflow.exceptions import NetworkError
from transflow.utils.http import HTTPClient


class TestHTTPClient:
    """Tests for HTTPClient class."""

    def test_init_default_values(self) -> None:
        """Test HTTPClient initializes with default configuration."""
        # Arrange & Act
        client = HTTPClient()

        # Assert
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.default_headers == {}

    def test_init_custom_values(self) -> None:
        """Test HTTPClient initializes with custom configuration."""
        # Arrange
        custom_headers = {"User-Agent": "TransFlow/1.0"}

        # Act
        client = HTTPClient(timeout=60, max_retries=5, headers=custom_headers)

        # Assert
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.default_headers == custom_headers

    @pytest.mark.asyncio
    async def test_get_success(self) -> None:
        """Test successful GET request returns response."""
        # Arrange
        client = HTTPClient()
        mock_response = httpx.Response(
            status_code=200,
            json={"data": "test"},
            request=httpx.Request("GET", "https://example.com"),
        )

        # Act
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
            response = await client.get("https://example.com")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"data": "test"}

    @pytest.mark.asyncio
    async def test_get_with_custom_headers(self) -> None:
        """Test GET request merges custom headers with defaults."""
        # Arrange
        default_headers = {"Authorization": "Bearer token"}
        custom_headers = {"Accept": "application/json"}
        client = HTTPClient(headers=default_headers)

        mock_get = AsyncMock(
            return_value=httpx.Response(
                status_code=200,
                request=httpx.Request("GET", "https://example.com"),
            )
        )

        # Act
        with patch("httpx.AsyncClient.get", new=mock_get):
            await client.get("https://example.com", headers=custom_headers)

        # Assert
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer token"
        assert call_kwargs["headers"]["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_network_error_raises_network_error(self) -> None:
        """Test GET request raises NetworkError on network failure."""
        # Arrange
        client = HTTPClient(max_retries=2)

        # Act & Assert
        with patch(
            "httpx.AsyncClient.get",
            new=AsyncMock(side_effect=httpx.NetworkError("Connection failed")),
        ):
            with pytest.raises(NetworkError):
                await client.get("https://example.com")

    @pytest.mark.asyncio
    async def test_post_success(self) -> None:
        """Test successful POST request returns response."""
        # Arrange
        client = HTTPClient()
        payload = {"key": "value"}
        mock_response = httpx.Response(
            status_code=201,
            json={"result": "created"},
            request=httpx.Request("POST", "https://example.com"),
        )

        # Act
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
            response = await client.post("https://example.com", json=payload)

        # Assert
        assert response.status_code == 201
        assert response.json() == {"result": "created"}

    @pytest.mark.asyncio
    async def test_post_timeout_raises_network_error(self) -> None:
        """Test POST request raises NetworkError on timeout."""
        # Arrange
        client = HTTPClient(max_retries=2, timeout=1)

        # Act & Assert
        with patch(
            "httpx.AsyncClient.post",
            new=AsyncMock(side_effect=httpx.TimeoutException("Timeout")),
        ):
            with pytest.raises(NetworkError):
                await client.post("https://example.com", json={})

    @pytest.mark.asyncio
    async def test_download_file_success(self) -> None:
        """Test successful file download writes content to disk."""
        # Arrange
        client = HTTPClient()
        url = "https://example.com/image.png"
        dest_path = "/tmp/image.png"
        mock_response = httpx.Response(
            status_code=200,
            content=b"fake image data",
            request=httpx.Request("GET", url),
        )

        # Act
        mock_open_context = MagicMock()
        mock_file = MagicMock()
        mock_open_context.__enter__ = MagicMock(return_value=mock_file)
        mock_open_context.__exit__ = MagicMock(return_value=False)
        
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
            with patch("builtins.open", return_value=mock_open_context) as mock_open:
                await client.download_file(url, dest_path)

        # Assert
        mock_open.assert_called_once_with(dest_path, "wb")
        mock_file.write.assert_called_once_with(b"fake image data")

    @pytest.mark.asyncio
    async def test_download_file_network_error(self) -> None:
        """Test file download raises NetworkError on failure."""
        # Arrange
        client = HTTPClient(max_retries=2)
        url = "https://example.com/image.png"

        # Act & Assert
        with patch(
            "httpx.AsyncClient.get",
            new=AsyncMock(side_effect=httpx.NetworkError("Failed")),
        ):
            with pytest.raises(NetworkError):
                await client.download_file(url, "/tmp/image.png")
