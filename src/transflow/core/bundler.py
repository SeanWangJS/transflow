"""Asset bundler for localizing images and creating self-contained packages."""

import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import yaml

from transflow.config import TransFlowConfig
from transflow.exceptions import NetworkError
from transflow.utils.filesystem import FileSystemHelper
from transflow.utils.http import HTTPClient


class AssetBundler:
    """Bundle Markdown with localized assets."""

    def __init__(self, config: TransFlowConfig):
        """
        Initialize bundler.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger("transflow.bundler")
        self.http_client = HTTPClient(
            timeout=config.http_timeout,
            max_retries=config.http_max_retries,
        )

    async def bundle(
        self,
        input_path: Path,
        output_dir: Path,
        folder_pattern: Optional[str] = None,
    ) -> Path:
        """
        Bundle Markdown file with localized assets.

        Args:
            input_path: Input Markdown file
            output_dir: Output directory root
            folder_pattern: Folder naming pattern (e.g., "{year}/{date}-{slug}")

        Returns:
            Path to the created bundle directory

        Raises:
            NetworkError: If asset download fails
        """
        try:
            # Read input file
            content = input_path.read_text(encoding="utf-8")
            self.logger.info(f"Bundling: {input_path}")

            # Extract metadata from frontmatter
            metadata = self._extract_frontmatter(content)
            title = metadata.get("title", input_path.stem)

            # Determine target directory
            if folder_pattern:
                folder_path = FileSystemHelper.format_folder_path(folder_pattern, title)
                bundle_dir = output_dir / folder_path
            else:
                slug = FileSystemHelper.generate_slug(title)
                bundle_dir = output_dir / slug

            # Create directory structure
            bundle_dir.mkdir(parents=True, exist_ok=True)
            assets_dir = bundle_dir / "assets"
            assets_dir.mkdir(exist_ok=True)

            # Extract image URLs
            image_urls = self._extract_image_urls(content)
            self.logger.info(f"Found {len(image_urls)} images to download")

            # Download images
            downloads = await self._download_assets(image_urls, assets_dir)

            # Update Markdown links
            updated_content = self._rewrite_image_links(content, downloads)

            # Write README.md
            readme_path = bundle_dir / "README.md"
            readme_path.write_text(updated_content, encoding="utf-8")

            # Generate meta.yaml
            meta = self._generate_metadata(metadata, downloads)
            meta_path = bundle_dir / "meta.yaml"
            meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")

            self.logger.info(f"Bundle created at: {bundle_dir}")

            return bundle_dir

        except Exception as e:
            self.logger.error(f"Bundling failed: {e}")
            raise

    def _extract_frontmatter(self, content: str) -> dict[str, str]:
        """
        Extract YAML frontmatter from Markdown.

        Args:
            content: Markdown content

        Returns:
            Dictionary of metadata
        """
        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(pattern, content, re.DOTALL)

        if match:
            try:
                return yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                return {}

        return {}

    def _extract_image_urls(self, content: str) -> list[str]:
        """
        Extract image URLs from Markdown.

        Args:
            content: Markdown content

        Returns:
            List of image URLs
        """
        # Pattern: ![alt](url) or ![alt](url "title")
        pattern = r"!\[.*?\]\(([^)\s]+)(?:\s+[\"'].*?[\"'])?\)"
        urls = re.findall(pattern, content)

        # Filter for HTTP/HTTPS URLs only
        return [url for url in urls if url.startswith(("http://", "https://"))]

    async def _download_assets(
        self,
        urls: list[str],
        dest_dir: Path,
    ) -> dict[str, str]:
        """
        Download assets with concurrent execution.

        Args:
            urls: List of asset URLs
            dest_dir: Destination directory

        Returns:
            Dictionary mapping original URL to local filename
        """
        if not urls:
            return {}

        # Limit concurrent downloads
        semaphore = asyncio.Semaphore(self.config.http_concurrent_downloads)
        downloads = {}

        async def download_one(url: str) -> tuple[str, Optional[str]]:
            async with semaphore:
                try:
                    filename = self._generate_asset_filename(url)
                    local_path = dest_dir / filename

                    self.logger.debug(f"Downloading: {url}")
                    await self.http_client.download_file(url, str(local_path))

                    return url, filename
                except Exception as e:
                    self.logger.warning(f"Failed to download {url}: {e}")
                    return url, None

        # Execute downloads concurrently
        results = await asyncio.gather(*[download_one(url) for url in urls])

        # Build mapping (skip failed downloads)
        for url, filename in results:
            if filename:
                downloads[url] = filename

        self.logger.info(f"Downloaded {len(downloads)}/{len(urls)} assets")

        return downloads

    def _generate_asset_filename(self, url: str) -> str:
        """
        Generate filename for downloaded asset.

        Args:
            url: Asset URL

        Returns:
            Filename with extension
        """
        parsed = urlparse(url)
        original_name = Path(parsed.path).name

        # If no name or extension, generate one
        if not original_name or "." not in original_name:
            # Use URL hash as filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            extension = ".jpg"  # Default extension
            return f"image_{url_hash}{extension}"

        # Sanitize filename
        safe_name = re.sub(r"[^\w\-.]", "_", original_name)

        return safe_name

    def _rewrite_image_links(self, content: str, downloads: dict[str, str]) -> str:
        """
        Rewrite image URLs to local paths.

        Args:
            content: Original Markdown content
            downloads: Mapping of URL to local filename

        Returns:
            Updated Markdown content
        """
        updated = content

        for url, filename in downloads.items():
            # Pattern: ![alt](url) or ![alt](url "title")
            # Replace with: ![alt](assets/filename)
            pattern = rf"!\[(.*?)\]\({re.escape(url)}(\s+[\"'].*?[\"'])?\)"
            replacement = rf"![\1](assets/{filename})"
            updated = re.sub(pattern, replacement, updated)

        return updated

    def _generate_metadata(
        self,
        frontmatter: dict[str, str],
        downloads: dict[str, str],
    ) -> dict[str, any]:
        """
        Generate bundle metadata.

        Args:
            frontmatter: Extracted frontmatter metadata
            downloads: Downloaded assets mapping

        Returns:
            Metadata dictionary
        """
        from datetime import datetime

        meta = {
            "bundled_at": datetime.now().isoformat(),
            "asset_count": len(downloads),
            "assets": list(downloads.values()),
        }

        # Include relevant frontmatter fields
        if "title" in frontmatter:
            meta["title"] = frontmatter["title"]
        if "source_url" in frontmatter:
            meta["source_url"] = frontmatter["source_url"]
        if "fetched_at" in frontmatter:
            meta["fetched_at"] = frontmatter["fetched_at"]

        return meta
