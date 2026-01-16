"""Configuration management utilities."""

import os
from enum import Enum
from typing import Any, Optional

from transflow.config import TransFlowConfig
from transflow.utils.logger import TransFlowLogger


class ConfigSource(Enum):
    """Configuration source."""

    ENVIRONMENT = "env"
    ENV_FILE = ".env"
    DEFAULT = "default"
    NOT_SET = "not set"


class ConfigItem:
    """Configuration item with metadata."""

    def __init__(
        self,
        key: str,
        value: Any,
        source: ConfigSource,
        category: str = "",
        description: str = "",
        required: bool = False,
    ):
        self.key = key
        self.value = value
        self.source = source
        self.category = category
        self.description = description
        self.required = required

    def display_value(self) -> str:
        """Get display value with masking for sensitive info."""
        if self.value is None or self.value == "":
            return "[NOT SET]"

        # Mask API keys
        if "api_key" in self.key.lower() and isinstance(self.value, str):
            if len(self.value) > 9:
                # Show first 5 and last 4 characters
                return f"{self.value[:5]}***{self.value[-4:]}"
            return "****"

        # Show full value for other configs
        return str(self.value)

    def source_display(self) -> str:
        """Get source display string."""
        if self.source == ConfigSource.ENVIRONMENT:
            env_var = f"TRANSFLOW_{self.key.upper()}"
            return f"({self.source.value}: {env_var})"
        elif self.source == ConfigSource.ENV_FILE:
            return f"({self.source.value})"
        elif self.source == ConfigSource.DEFAULT:
            return f"({self.source.value})"
        else:
            return ""

    def status_display(self) -> str:
        """Get status indicator."""
        if self.value is None or self.value == "":
            if self.required:
                return "[MISSING]"
            return "[OPTIONAL]"
        return "[SET]"


def get_config_items() -> dict[str, list[ConfigItem]]:
    """
    Get all configuration items grouped by category.

    Returns:
        Dictionary mapping category to list of ConfigItem
    """
    config = TransFlowConfig()

    items = {
        "API Configuration": [
            ConfigItem(
                "openai_api_key",
                config.openai_api_key,
                _get_source("TRANSFLOW_OPENAI_API_KEY"),
                category="API",
                description="OpenAI/LLM API key for translations",
                required=True,
            ),
            ConfigItem(
                "openai_base_url",
                config.openai_base_url,
                _get_source("TRANSFLOW_OPENAI_BASE_URL", "https://api.openai.com/v1"),
                category="API",
                description="OpenAI/LLM API base URL",
                required=False,
            ),
            ConfigItem(
                "openai_model",
                config.openai_model,
                _get_source("TRANSFLOW_OPENAI_MODEL", "gpt-4o"),
                category="API",
                description="LLM model name to use",
                required=False,
            ),
        ],
        "Extraction Configuration": [
            ConfigItem(
                "firecrawl_api_key",
                config.firecrawl_api_key,
                _get_source("TRANSFLOW_FIRECRAWL_API_KEY"),
                category="Extraction",
                description="Firecrawl API key for web extraction",
                required=False,
            ),
            ConfigItem(
                "firecrawl_base_url",
                config.firecrawl_base_url,
                _get_source("TRANSFLOW_FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v1"),
                category="Extraction",
                description="Firecrawl API base URL",
                required=False,
            ),
            ConfigItem(
                "firecrawl_timeout",
                config.firecrawl_timeout,
                _get_source("TRANSFLOW_FIRECRAWL_TIMEOUT", "30"),
                category="Extraction",
                description="Firecrawl request timeout (seconds)",
                required=False,
            ),
        ],
        "HTTP Configuration": [
            ConfigItem(
                "http_timeout",
                config.http_timeout,
                _get_source("TRANSFLOW_HTTP_TIMEOUT", "30"),
                category="HTTP",
                description="HTTP request timeout (seconds)",
                required=False,
            ),
            ConfigItem(
                "http_max_retries",
                config.http_max_retries,
                _get_source("TRANSFLOW_HTTP_MAX_RETRIES", "3"),
                category="HTTP",
                description="Maximum HTTP retry attempts",
                required=False,
            ),
            ConfigItem(
                "http_concurrent_downloads",
                config.http_concurrent_downloads,
                _get_source("TRANSFLOW_HTTP_CONCURRENT_DOWNLOADS", "5"),
                category="HTTP",
                description="Maximum concurrent downloads",
                required=False,
            ),
        ],
        "Logging Configuration": [
            ConfigItem(
                "log_level",
                config.log_level,
                _get_source("TRANSFLOW_LOG_LEVEL", "INFO"),
                category="Logging",
                description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
                required=False,
            ),
            ConfigItem(
                "log_file",
                config.log_file,
                _get_source("TRANSFLOW_LOG_FILE"),
                category="Logging",
                description="Log file path (optional)",
                required=False,
            ),
            ConfigItem(
                "log_json",
                config.log_json,
                _get_source("TRANSFLOW_LOG_JSON", "False"),
                category="Logging",
                description="Use JSON log format",
                required=False,
            ),
        ],
        "Default Language": [
            ConfigItem(
                "default_language",
                config.default_language,
                _get_source("TRANSFLOW_DEFAULT_LANGUAGE", "zh"),
                category="Language",
                description="Default target language for translations",
                required=False,
            ),
        ],
    }

    return items


def _get_source(env_key: str, default_value: Any = None) -> ConfigSource:
    """
    Determine configuration source.

    Args:
        env_key: Environment variable key to check
        default_value: Default value if not in environment

    Returns:
        ConfigSource enum value
    """
    if os.getenv(env_key):
        return ConfigSource.ENVIRONMENT
    elif default_value is not None:
        return ConfigSource.DEFAULT
    else:
        return ConfigSource.NOT_SET


def validate_config() -> tuple[bool, list[str], list[str]]:
    """
    Validate configuration.

    Returns:
        (is_valid, warnings, errors)
    """
    from pydantic import ValidationError
    from pydantic_settings import SettingsConfigDict

    warnings = []
    errors = []

    # Create a validation config that doesn't load from .env file
    # This ensures we validate only the current runtime environment
    class _ValidationConfig(TransFlowConfig):
        model_config = SettingsConfigDict(
            env_prefix="TRANSFLOW_",
            env_file=None,  # Don't load from .env during validation
            env_file_encoding="utf-8",
            case_sensitive=False,
            populate_by_name=True,
        )

    # Try to load config, catching validation errors
    try:
        config = _ValidationConfig()
    except ValidationError as e:
        # Extract validation errors from Pydantic
        for error in e.errors():
            field = error.get("loc", ["unknown"])[0]
            msg = error.get("msg", "validation error")
            errors.append(f"{field}: {msg}")
        # If there are validation errors, return early
        return False, warnings, errors

    # Check required configs
    if not config.openai_api_key:
        errors.append(
            "openai_api_key is required for 'translate' command. "
            "Set it with: export TRANSFLOW_OPENAI_API_KEY=your_key"
        )

    # Check optional but useful configs
    if not config.firecrawl_api_key:
        warnings.append(
            "firecrawl_api_key is not set. 'download' command will not work. "
            "Set it with: export TRANSFLOW_FIRECRAWL_API_KEY=your_key"
        )

    # Validate timeout values
    if config.http_timeout <= 0:
        errors.append(f"http_timeout must be positive, got {config.http_timeout}")

    if config.firecrawl_timeout <= 0:
        errors.append(f"firecrawl_timeout must be positive, got {config.firecrawl_timeout}")

    # Validate concurrent downloads
    if config.http_concurrent_downloads < 1 or config.http_concurrent_downloads > 20:
        errors.append(
            f"http_concurrent_downloads must be between 1 and 20, "
            f"got {config.http_concurrent_downloads}"
        )

    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if config.log_level.upper() not in valid_levels:
        errors.append(f"log_level must be one of {valid_levels}, got {config.log_level}")

    is_valid = len(errors) == 0

    return is_valid, warnings, errors
