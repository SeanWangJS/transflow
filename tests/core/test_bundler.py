"""Tests for asset bundler.

Following Google Python testing guidelines.
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from transflow.config import TransFlowConfig
from transflow.core.bundler import AssetBundler


class TestAssetBundler:
    """Tests for AssetBundler class."""

    def test_init_creates_http_client(self) -> None:
        """Test bundler initialization creates HTTP client."""
        # Arrange
        config = TransFlowConfig()

        # Act
        bundler = AssetBundler(config)

        # Assert
        assert bundler.config == config
        assert bundler.http_client is not None

    @pytest.mark.asyncio
    async def test_bundle_creates_directory_structure(self) -> None:
        """Test bundle creates output directory and assets folder."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        input_content = "---\ntitle: Test\n---\n\n# Test"
        input_path = Path("/tmp/test.md")
        output_dir = Path("/tmp/output")

        mkdir_calls = []

        def track_mkdir(*args, **kwargs):
            mkdir_calls.append(args[0] if args else kwargs.get("self"))

        # Act
        with patch.object(Path, "read_text", return_value=input_content):
            with patch.object(Path, "write_text"):
                with patch.object(Path, "mkdir", side_effect=track_mkdir):
                    result = await bundler.bundle(input_path, output_dir)

        # Assert
        assert isinstance(result, Path)
        assert len(mkdir_calls) >= 2  # bundle_dir and assets_dir

    @pytest.mark.asyncio
    async def test_bundle_downloads_images(self) -> None:
        """Test bundle downloads remote images."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        input_content = "---\ntitle: Test\n---\n\n![Image](https://example.com/image.png)"
        input_path = Path("/tmp/test.md")
        output_dir = Path("/tmp/output")

        mock_download = AsyncMock()

        # Act
        with patch.object(Path, "read_text", return_value=input_content):
            with patch.object(Path, "write_text"):
                with patch.object(Path, "mkdir"):
                    with patch.object(
                        bundler.http_client,
                        "download_file",
                        new=mock_download,
                    ):
                        await bundler.bundle(input_path, output_dir)

        # Assert
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        assert "https://example.com/image.png" in call_args[0]

    @pytest.mark.asyncio
    async def test_bundle_rewrites_image_links(self) -> None:
        """Test bundle rewrites remote image URLs to local paths."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        input_content = "![Alt](https://example.com/img.png)"
        input_path = Path("/tmp/test.md")
        output_dir = Path("/tmp/output")

        write_calls: list[tuple[str, str]] = []

        def capture_write(content: str, **kwargs: Any) -> None:
            write_calls.append(("readme", content))

        # Act
        with patch.object(Path, "read_text", return_value=input_content):
            with patch.object(Path, "write_text", side_effect=capture_write):
                with patch.object(Path, "mkdir"):
                    with patch.object(bundler.http_client, "download_file", new=AsyncMock()):
                        await bundler.bundle(input_path, output_dir)

        # Assert
        assert len(write_calls) > 0
        # First call is the README.md content
        readme_content = write_calls[0][1]
        assert "assets/" in readme_content
        assert "https://example.com" not in readme_content

    @pytest.mark.asyncio
    async def test_bundle_creates_meta_yaml(self) -> None:
        """Test bundle generates meta.yaml file."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        input_content = "---\ntitle: Test Article\nsource_url: https://example.com\n---\n\nContent"
        input_path = Path("/tmp/test.md")
        output_dir = Path("/tmp/output")

        write_calls: list[str] = []

        def track_write(content: str, **kwargs: Any) -> None:
            write_calls.append(content)

        # Act
        with patch.object(Path, "read_text", return_value=input_content):
            with patch.object(Path, "write_text", side_effect=track_write):
                with patch.object(Path, "mkdir"):
                    await bundler.bundle(input_path, output_dir)

        # Assert
        # Second call should be the meta.yaml (first is README.md)
        assert len(write_calls) >= 2
        meta_content = write_calls[1]
        assert "title: Test Article" in meta_content
        assert "bundled_at:" in meta_content

    def test_extract_frontmatter_parses_yaml(self) -> None:
        """Test frontmatter extraction parses YAML correctly."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        content = "---\ntitle: Test\nauthor: John\n---\n\nContent"

        # Act
        metadata = bundler._extract_frontmatter(content)

        # Assert
        assert metadata["title"] == "Test"
        assert metadata["author"] == "John"

    def test_extract_frontmatter_handles_no_frontmatter(self) -> None:
        """Test frontmatter extraction returns empty dict when none present."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        content = "# Title\n\nContent"

        # Act
        metadata = bundler._extract_frontmatter(content)

        # Assert
        assert metadata == {}

    def test_extract_image_urls_finds_markdown_images(self) -> None:
        """Test image URL extraction finds Markdown image syntax."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        content = "![Alt1](https://example.com/img1.png) and ![Alt2](https://example.com/img2.jpg)"

        # Act
        urls = bundler._extract_image_urls(content)

        # Assert
        assert len(urls) == 2
        assert "https://example.com/img1.png" in urls
        assert "https://example.com/img2.jpg" in urls

    def test_extract_image_urls_ignores_relative_paths(self) -> None:
        """Test image URL extraction ignores relative image paths."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        content = "![Remote](https://example.com/img.png) and ![Local](./local.png)"

        # Act
        urls = bundler._extract_image_urls(content)

        # Assert
        assert len(urls) == 1
        assert "https://example.com/img.png" in urls
        assert "./local.png" not in urls

    def test_extract_image_urls_handles_image_titles(self) -> None:
        """Test image URL extraction handles images with title attributes."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        content = '![Alt](https://example.com/img.png "Image Title")'

        # Act
        urls = bundler._extract_image_urls(content)

        # Assert
        assert len(urls) == 1
        assert "https://example.com/img.png" in urls

    @pytest.mark.asyncio
    async def test_download_assets_concurrent_execution(self) -> None:
        """Test asset download uses concurrent execution."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        urls = [f"https://example.com/img{i}.png" for i in range(5)]
        dest_dir = Path("/tmp/assets")

        download_calls = []

        async def track_download(url, path):
            download_calls.append(url)
            await asyncio.sleep(0.01)  # Simulate download time

        # Act
        with patch.object(bundler.http_client, "download_file", side_effect=track_download):
            result = await bundler._download_assets(urls, dest_dir)

        # Assert
        assert len(download_calls) == 5
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_download_assets_handles_failures_gracefully(self) -> None:
        """Test asset download continues when individual downloads fail."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        urls = ["https://example.com/good.png", "https://example.com/bad.png"]
        dest_dir = Path("/tmp/assets")

        async def mock_download(url, path):
            if "bad" in url:
                raise Exception("Download failed")

        # Act
        with patch.object(bundler.http_client, "download_file", side_effect=mock_download):
            result = await bundler._download_assets(urls, dest_dir)

        # Assert
        assert len(result) == 1  # Only successful download
        assert "good.png" in str(result.values())

    def test_generate_asset_filename_from_url(self) -> None:
        """Test asset filename generation from URL."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        url = "https://example.com/path/to/image.png"

        # Act
        filename = bundler._generate_asset_filename(url)

        # Assert
        assert filename == "image.png"

    def test_generate_asset_filename_handles_no_extension(self) -> None:
        """Test asset filename generation provides default for URLs without extension."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        url = "https://example.com/image"

        # Act
        filename = bundler._generate_asset_filename(url)

        # Assert
        assert filename.startswith("image_")
        assert filename.endswith(".jpg")

    def test_rewrite_image_links_updates_urls(self) -> None:
        """Test image link rewriting replaces URLs with local paths."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        content = "![Alt](https://example.com/img.png)"
        downloads = {"https://example.com/img.png": "img.png"}

        # Act
        result = bundler._rewrite_image_links(content, downloads)

        # Assert
        assert "assets/img.png" in result
        assert "https://example.com/img.png" not in result

    def test_generate_metadata_includes_bundle_info(self) -> None:
        """Test metadata generation includes bundle information."""
        # Arrange
        config = TransFlowConfig()
        bundler = AssetBundler(config)

        frontmatter = {"title": "Test", "source_url": "https://example.com"}
        downloads = {"https://example.com/img1.png": "img1.png"}

        # Act
        metadata = bundler._generate_metadata(frontmatter, downloads)

        # Assert
        assert "bundled_at" in metadata
        assert metadata["asset_count"] == 1
        assert metadata["title"] == "Test"
        assert metadata["source_url"] == "https://example.com"
        assert "img1.png" in metadata["assets"]
