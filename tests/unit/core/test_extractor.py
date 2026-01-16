"""Tests for Markdown extractor.

Following Google Python testing guidelines:
- Descriptive test names indicating test scenario and expected outcome
- Arrange-Act-Assert structure
- Mock external dependencies (HTTP calls, file I/O)
- Test both success and error paths
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from transflow.config import TransFlowConfig
from transflow.core.extractor import MarkdownDocument, MarkdownExtractor
from transflow.exceptions import APIError, ValidationError


class TestMarkdownDocument:
    """Tests for MarkdownDocument class."""

    def test_init_with_default_timestamp(self) -> None:
        """Test MarkdownDocument initializes with current timestamp when not provided."""
        # Arrange
        content = "# Test"
        title = "Test Article"
        url = "https://example.com"

        # Act
        doc = MarkdownDocument(content=content, title=title, source_url=url)

        # Assert
        assert doc.content == content
        assert doc.title == title
        assert doc.source_url == url
        assert isinstance(doc.fetched_at, datetime)

    def test_init_with_custom_timestamp(self) -> None:
        """Test MarkdownDocument accepts custom timestamp."""
        # Arrange
        content = "# Test"
        title = "Test"
        url = "https://example.com"
        custom_time = datetime(2026, 1, 14, 12, 0, 0)

        # Act
        doc = MarkdownDocument(
            content=content,
            title=title,
            source_url=url,
            fetched_at=custom_time,
        )

        # Assert
        assert doc.fetched_at == custom_time

    def test_to_markdown_with_frontmatter_includes_metadata(self) -> None:
        """Test Markdown export includes YAML frontmatter with metadata."""
        # Arrange
        doc = MarkdownDocument(
            content="# Test Content",
            title="Test Article",
            source_url="https://example.com/article",
            fetched_at=datetime(2026, 1, 14, 12, 0, 0),
        )

        # Act
        result = doc.to_markdown_with_frontmatter()

        # Assert
        assert result.startswith("---\n")
        assert "title: Test Article" in result
        assert "source_url: https://example.com/article" in result
        assert "fetched_at:" in result
        assert "2026-01-14" in result
        assert "# Test Content" in result


class TestMarkdownExtractor:
    """Tests for MarkdownExtractor class."""

    def test_init_without_api_key_raises_error(self) -> None:
        """Test extractor initialization fails when API key is missing."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="")

        # Act & Assert
        with pytest.raises(ValidationError, match="Firecrawl API key is required"):
            MarkdownExtractor(config)

    def test_init_with_valid_config(self) -> None:
        """Test extractor initializes successfully with valid configuration."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")

        # Act
        extractor = MarkdownExtractor(config)

        # Assert
        assert extractor.config == config
        assert extractor.http_client is not None

    def test_validate_url_accepts_http_scheme(self) -> None:
        """Test URL validation accepts HTTP scheme."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        # Act
        result = extractor.validate_url("http://example.com")

        # Assert
        assert result is True

    def test_validate_url_accepts_https_scheme(self) -> None:
        """Test URL validation accepts HTTPS scheme."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        # Act
        result = extractor.validate_url("https://example.com")

        # Assert
        assert result is True

    def test_validate_url_rejects_invalid_scheme(self) -> None:
        """Test URL validation rejects non-HTTP schemes."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid URL scheme"):
            extractor.validate_url("ftp://example.com")

    def test_validate_url_rejects_missing_domain(self) -> None:
        """Test URL validation rejects URLs without domain."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        # Act & Assert
        with pytest.raises(ValidationError, match="Missing domain"):
            extractor.validate_url("https://")

    @pytest.mark.asyncio
    async def test_fetch_success_returns_document(self) -> None:
        """Test successful fetch returns MarkdownDocument with content."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "markdown": "# Test Article\n\nContent here.",
                "metadata": {"title": "Test Article"},
            },
        }

        # Act
        with patch.object(
            extractor.http_client,
            "post",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await extractor.fetch("https://example.com/article")

        # Assert
        assert isinstance(result, MarkdownDocument)
        assert result.content == "# Test Article\n\nContent here."
        assert result.title == "Test Article"
        assert result.source_url == "https://example.com/article"

    @pytest.mark.asyncio
    async def test_fetch_api_error_raises_api_error(self) -> None:
        """Test fetch raises APIError when Firecrawl returns error."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Rate limit exceeded",
        }

        # Act & Assert
        with patch.object(
            extractor.http_client,
            "post",
            new=AsyncMock(return_value=mock_response),
        ):
            with pytest.raises(APIError, match="Rate limit exceeded"):
                await extractor.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_empty_content_raises_error(self) -> None:
        """Test fetch raises APIError when content is empty."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"markdown": ""},
        }

        # Act & Assert
        with patch.object(
            extractor.http_client,
            "post",
            new=AsyncMock(return_value=mock_response),
        ):
            with pytest.raises(APIError, match="empty content"):
                await extractor.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_invalid_url_raises_validation_error(self) -> None:
        """Test fetch validates URL before making API call."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        # Act & Assert
        with pytest.raises(ValidationError):
            await extractor.fetch("invalid-url")

    @pytest.mark.asyncio
    async def test_fetch_and_save_creates_file(self) -> None:
        """Test fetch_and_save writes content to file system."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        mock_document = MarkdownDocument(
            content="# Test",
            title="Test",
            source_url="https://example.com",
        )

        output_path = Path("/tmp/test.md")

        # Act
        with patch.object(extractor, "fetch", new=AsyncMock(return_value=mock_document)):
            with patch.object(Path, "write_text") as mock_write:
                with patch.object(Path, "mkdir"):
                    result = await extractor.fetch_and_save(
                        "https://example.com",
                        output_path,
                    )

        # Assert
        assert result == output_path
        mock_write.assert_called_once()
        written_content = mock_write.call_args[0][0]
        assert "---" in written_content
        assert "# Test" in written_content

    @pytest.mark.asyncio
    async def test_fetch_and_save_auto_generates_filename(self) -> None:
        """Test fetch_and_save generates filename when not provided."""
        # Arrange
        config = TransFlowConfig(firecrawl_api_key="test_key")
        extractor = MarkdownExtractor(config)

        mock_document = MarkdownDocument(
            content="# Test",
            title="Test",
            source_url="https://example.com/my-article",
        )

        # Act
        with patch.object(extractor, "fetch", new=AsyncMock(return_value=mock_document)):
            with patch.object(Path, "write_text"):
                with patch.object(Path, "mkdir"):
                    result = await extractor.fetch_and_save("https://example.com/my-article")

        # Assert
        assert result.name == "my-article.md"
