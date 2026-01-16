"""Tests for filesystem utilities.

Following Google Python testing guidelines:
- Clear test function names describing behavior under test
- Arrange-Act-Assert pattern
- One assertion per logical concept
- Comprehensive docstrings
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from transflow.utils.filesystem import FileSystemHelper


class TestFileSystemHelper:
    """Tests for FileSystemHelper utility class."""

    def test_generate_slug_basic(self) -> None:
        """Test slug generation from simple text."""
        # Arrange
        text = "Hello World"

        # Act
        slug = FileSystemHelper.generate_slug(text)

        # Assert
        assert slug == "hello-world"

    def test_generate_slug_with_special_characters(self) -> None:
        """Test slug generation removes special characters."""
        # Arrange
        text = "Test: Article & Title!"

        # Act
        slug = FileSystemHelper.generate_slug(text)

        # Assert
        assert slug == "test-article-title"

    def test_generate_slug_with_max_length(self) -> None:
        """Test slug generation respects max length constraint."""
        # Arrange
        text = "This is a very long title that should be truncated"
        max_length = 20

        # Act
        slug = FileSystemHelper.generate_slug(text, max_length=max_length)

        # Assert
        assert len(slug) <= max_length

    def test_generate_slug_chinese_characters(self) -> None:
        """Test slug generation handles non-ASCII characters."""
        # Arrange
        text = "测试文章标题"

        # Act
        slug = FileSystemHelper.generate_slug(text)

        # Assert
        assert slug == "ce-shi-wen-zhang-biao-ti"

    def test_generate_filename_from_url_simple(self) -> None:
        """Test filename generation from simple URL."""
        # Arrange
        url = "https://example.com/my-article"

        # Act
        filename = FileSystemHelper.generate_filename_from_url(url)

        # Assert
        assert filename == "my-article.md"

    def test_generate_filename_from_url_with_query_params(self) -> None:
        """Test filename generation strips query parameters."""
        # Arrange
        url = "https://example.com/article?id=123&lang=en"

        # Act
        filename = FileSystemHelper.generate_filename_from_url(url)

        # Assert
        assert filename == "article.md"
        assert "?" not in filename

    def test_generate_filename_from_url_with_anchor(self) -> None:
        """Test filename generation strips anchor tags."""
        # Arrange
        url = "https://example.com/article#section"

        # Act
        filename = FileSystemHelper.generate_filename_from_url(url)

        # Assert
        assert filename == "article.md"
        assert "#" not in filename

    def test_generate_filename_from_url_with_trailing_slash(self) -> None:
        """Test filename generation handles trailing slash."""
        # Arrange
        url = "https://example.com/my-article/"

        # Act
        filename = FileSystemHelper.generate_filename_from_url(url)

        # Assert
        assert filename == "my-article.md"

    def test_generate_filename_from_url_fallback(self) -> None:
        """Test filename generation provides fallback for root URLs."""
        # Arrange
        url = "https://example.com/"

        # Act
        filename = FileSystemHelper.generate_filename_from_url(url)

        # Assert
        assert filename.endswith(".md")
        assert len(filename) > 3

    def test_ensure_directory_creates_new_directory(self) -> None:
        """Test ensure_directory creates non-existent directory."""
        # Arrange
        test_path = Path("/tmp/test_transflow_dir")

        # Act
        with patch.object(Path, "mkdir") as mock_mkdir:
            FileSystemHelper.ensure_directory(test_path)

        # Assert
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_generate_unique_filename_no_collision(self) -> None:
        """Test unique filename generation when no file exists."""
        # Arrange
        directory = Path("/tmp")
        base_name = "test"
        extension = ".md"

        # Act
        with patch.object(Path, "exists", return_value=False):
            filename = FileSystemHelper.generate_unique_filename(directory, base_name, extension)

        # Assert
        assert filename == "test.md"

    def test_generate_unique_filename_with_collision(self) -> None:
        """Test unique filename generation adds hash suffix on collision."""
        # Arrange
        directory = Path("/tmp")
        base_name = "test"
        extension = ".md"

        # Act
        with patch.object(Path, "exists", return_value=True):
            filename = FileSystemHelper.generate_unique_filename(directory, base_name, extension)

        # Assert
        assert filename.startswith("test_")
        assert filename.endswith(".md")
        assert len(filename) == len("test_") + 8 + len(".md")  # 8-char hash

    def test_format_folder_path_basic(self) -> None:
        """Test folder path formatting with basic pattern."""
        # Arrange
        pattern = "{year}/{slug}"
        title = "Test Article"
        date = datetime(2026, 1, 14)

        # Act
        result = FileSystemHelper.format_folder_path(pattern, title, date)

        # Assert
        assert result == "2026/test-article"

    def test_format_folder_path_complex_pattern(self) -> None:
        """Test folder path formatting with complex date pattern."""
        # Arrange
        pattern = "{year}/{month}/{day}-{slug}"
        title = "My Article"
        date = datetime(2026, 1, 14)

        # Act
        result = FileSystemHelper.format_folder_path(pattern, title, date)

        # Assert
        assert result == "2026/01/14-my-article"

    def test_format_folder_path_with_date_token(self) -> None:
        """Test folder path formatting uses {date} token correctly."""
        # Arrange
        pattern = "{year}/{date}-{slug}"
        title = "Test"
        date = datetime(2026, 1, 14)

        # Act
        result = FileSystemHelper.format_folder_path(pattern, title, date)

        # Assert
        assert result == "2026/20260114-test"

    def test_format_folder_path_defaults_to_current_date(self) -> None:
        """Test folder path formatting uses current date when not provided."""
        # Arrange
        pattern = "{year}/{slug}"
        title = "Test"

        # Act
        with patch("transflow.utils.filesystem.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 14)
            result = FileSystemHelper.format_folder_path(pattern, title)

        # Assert
        assert result.startswith("2026/")
