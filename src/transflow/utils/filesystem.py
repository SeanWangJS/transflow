"""Filesystem utilities."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from slugify import slugify


class FileSystemHelper:
    """Helper for filesystem operations."""

    @staticmethod
    def generate_slug(text: str, max_length: int = 50) -> str:
        """
        Generate URL-safe slug from text.

        Args:
            text: Input text
            max_length: Maximum slug length

        Returns:
            Slugified string
        """
        return slugify(text, max_length=max_length)

    @staticmethod
    def generate_filename_from_url(url: str) -> str:
        """
        Generate filename from URL.

        Args:
            url: Source URL

        Returns:
            Generated filename with .md extension
        """
        from urllib.parse import urlparse
        
        # Parse URL to get path
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        
        # Extract meaningful part from path
        if path and path != "/":
            parts = path.split("/")
            title = parts[-1] if parts else "article"
        else:
            # Use domain name or fallback to "article"
            title = "article"

        # Remove query params and anchors
        title = title.split("?")[0].split("#")[0]

        # Generate slug
        slug = FileSystemHelper.generate_slug(title)
        if not slug:
            slug = "article"

        return f"{slug}.md"

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """
        Ensure directory exists, create if necessary.

        Args:
            path: Directory path
        """
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_unique_filename(directory: Path, base_name: str, extension: str) -> str:
        """
        Generate unique filename by adding hash suffix if collision occurs.

        Args:
            directory: Target directory
            base_name: Base filename without extension
            extension: File extension (with dot)

        Returns:
            Unique filename
        """
        filename = f"{base_name}{extension}"
        filepath = directory / filename

        if not filepath.exists():
            return filename

        # Generate hash suffix
        hash_suffix = hashlib.md5(
            (base_name + str(datetime.now().timestamp())).encode()
        ).hexdigest()[:8]

        return f"{base_name}_{hash_suffix}{extension}"

    @staticmethod
    def format_folder_path(
        pattern: str,
        title: str,
        date: Optional[datetime] = None,
    ) -> str:
        """
        Format folder path using pattern template.

        Args:
            pattern: Format pattern (e.g., "{year}/{date}-{slug}")
            title: Article title
            date: Optional date (defaults to now)

        Returns:
            Formatted folder path
        """
        if date is None:
            date = datetime.now()

        slug = FileSystemHelper.generate_slug(title)

        replacements = {
            "{year}": str(date.year),
            "{month}": f"{date.month:02d}",
            "{day}": f"{date.day:02d}",
            "{date}": date.strftime("%Y%m%d"),
            "{slug}": slug,
        }

        result = pattern
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result
