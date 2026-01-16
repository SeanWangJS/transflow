"""HTTP client utilities with retry logic."""

import asyncio
from typing import Any, Optional

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from transflow.exceptions import NetworkError


class HTTPClient:
    """Async HTTP client with automatic retry logic."""

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        headers: Optional[dict[str, str]] = None,
    ):
        """
        Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            headers: Optional default headers
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = headers or {}

    async def get(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute GET request with retry logic.

        Args:
            url: Target URL
            headers: Optional request headers
            **kwargs: Additional httpx request parameters

        Returns:
            HTTP response

        Raises:
            NetworkError: If request fails after retries
        """
        merged_headers = {**self.default_headers, **(headers or {})}

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
            ),
            reraise=True,
        )
        async def _get_with_retry() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=merged_headers, **kwargs)
                response.raise_for_status()
                return response

        try:
            return await _get_with_retry()
        except RetryError as e:
            raise NetworkError(f"Failed to fetch {url} after {self.max_retries} retries") from e
        except httpx.HTTPError as e:
            raise NetworkError(f"HTTP error fetching {url}: {e}") from e

    async def post(
        self,
        url: str,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute POST request with retry logic.

        Args:
            url: Target URL
            json: JSON payload
            headers: Optional request headers
            **kwargs: Additional httpx request parameters

        Returns:
            HTTP response

        Raises:
            NetworkError: If request fails after retries
        """
        merged_headers = {**self.default_headers, **(headers or {})}

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
            ),
            reraise=True,
        )
        async def _post_with_retry() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=json, headers=merged_headers, **kwargs)
                response.raise_for_status()
                return response

        try:
            return await _post_with_retry()
        except RetryError as e:
            raise NetworkError(f"Failed to post to {url} after {self.max_retries} retries") from e
        except httpx.HTTPError as e:
            raise NetworkError(f"HTTP error posting to {url}: {e}") from e

    async def download_file(
        self,
        url: str,
        dest_path: str,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Download file from URL to local path.

        Args:
            url: Source URL
            dest_path: Destination file path
            headers: Optional request headers

        Raises:
            NetworkError: If download fails
        """
        response = await self.get(url, headers=headers)
        
        with open(dest_path, "wb") as f:
            f.write(response.content)
