"""Markdown extractor using Firecrawl API."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import yaml

from transflow.config import TransFlowConfig
from transflow.exceptions import APIError, ValidationError
from transflow.utils.filesystem import FileSystemHelper
from transflow.utils.http import HTTPClient


class MarkdownDocument:
    """Container for Markdown document with metadata."""

    def __init__(
        self,
        content: str,
        title: str,
        source_url: str,
        fetched_at: Optional[datetime] = None,
    ):
        """
        Initialize Markdown document.

        Args:
            content: Markdown content
            title: Document title
            source_url: Source URL
            fetched_at: Fetch timestamp (defaults to now)
        """
        self.content = content
        self.title = title
        self.source_url = source_url
        self.fetched_at = fetched_at or datetime.now()

    def to_markdown_with_frontmatter(self) -> str:
        """
        Convert to Markdown with YAML frontmatter.

        Returns:
            Complete Markdown document with metadata
        """
        frontmatter = {
            "title": self.title,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at.isoformat(),
        }

        yaml_content = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)

        return f"---\n{yaml_content}---\n\n{self.content}"


class MarkdownExtractor:
    """Extract web content and convert to Markdown using Firecrawl."""

    def __init__(self, config: TransFlowConfig):
        """
        Initialize extractor.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger("transflow.extractor")

        if not config.firecrawl_api_key:
            raise ValidationError("Firecrawl API key is required (TRANSFLOW_FIRECRAWL_API_KEY)")

        self.http_client = HTTPClient(
            timeout=config.firecrawl_timeout,
            max_retries=config.http_max_retries,
            headers={"Authorization": f"Bearer {config.firecrawl_api_key}"},
        )

    def validate_url(self, url: str) -> bool:
        """
        Validate URL format and scheme.

        Args:
            url: URL to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If URL is invalid
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise ValidationError(f"Invalid URL scheme: {parsed.scheme}. Must be http or https")
            if not parsed.netloc:
                raise ValidationError(f"Invalid URL: {url}. Missing domain")
            return True
        except Exception as e:
            raise ValidationError(f"Invalid URL: {url}. Error: {e}") from e

    async def fetch(self, url: str) -> MarkdownDocument:
        """
        Fetch web content and convert to Markdown.

        Args:
            url: Target URL

        Returns:
            MarkdownDocument with content and metadata

        Raises:
            ValidationError: If URL is invalid
            APIError: If Firecrawl API fails
        """
        self.validate_url(url)
        self.logger.info(f"Fetching content from: {url}")

        try:
            # Call Firecrawl API
            api_url = f"{self.config.firecrawl_base_url}/scrape"
            response = await self.http_client.post(
                api_url,
                json={
                    "url": url,
                    "formats": ["markdown"],
                },
            )

            data = response.json()

            # Extract content from response
            if not data.get("success"):
                raise APIError(f"Firecrawl API returned error: {data.get('error', 'Unknown error')}")

            markdown_content = data.get("data", {}).get("markdown", "")
            if not markdown_content:
                raise APIError("Firecrawl returned empty content")

            title = data.get("data", {}).get("metadata", {}).get("title", "Untitled")

            self.logger.info(f"Successfully fetched content (title: {title})")

            return MarkdownDocument(
                content=markdown_content,
                title=title,
                source_url=url,
            )

        except APIError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to fetch content: {e}")
            raise APIError(f"Firecrawl API error: {e}") from e

    async def fetch_and_save(self, url: str, output_path: Optional[Path] = None) -> Path:
        """
        Fetch content and save to file.

        Args:
            url: Source URL
            output_path: Output file path (auto-generated if None)

        Returns:
            Path to saved file

        Raises:
            ValidationError: If URL or path is invalid
            APIError: If fetch fails
        """
        document = await self.fetch(url)

        if output_path is None:
            filename = FileSystemHelper.generate_filename_from_url(url)
            output_path = Path.cwd() / filename

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        markdown_with_frontmatter = document.to_markdown_with_frontmatter()
        output_path.write_text(markdown_with_frontmatter, encoding="utf-8")

        self.logger.info(f"Saved to: {output_path}")

        return output_path
