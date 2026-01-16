"""Configuration management for TransFlow."""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TransFlowConfig(BaseSettings):
    """Application configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="TRANSFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Firecrawl settings
    firecrawl_api_key: str = Field(default="", description="Firecrawl API key")
    firecrawl_timeout: int = Field(default=30, description="Request timeout in seconds")
    firecrawl_base_url: str = Field(
        default="https://api.firecrawl.dev/v1",
        description="Firecrawl API base URL",
    )

    # LLM settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL",
    )
    default_model: str = Field(default="gpt-4o", description="Default LLM model")
    default_language: str = Field(default="zh", description="Default target language")

    # HTTP settings
    http_timeout: int = Field(default=30, description="HTTP timeout in seconds")
    http_max_retries: int = Field(default=3, description="Maximum HTTP retry attempts")
    http_concurrent_downloads: int = Field(
        default=5,
        description="Maximum concurrent downloads",
    )

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[Path] = Field(default=None, description="Log file path")
    log_json: bool = Field(default=False, description="Use JSON log format")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v

    @field_validator("http_timeout", "firecrawl_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout values."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @field_validator("http_concurrent_downloads")
    @classmethod
    def validate_concurrent_downloads(cls, v: int) -> int:
        """Validate concurrent downloads."""
        if v < 1 or v > 20:
            raise ValueError("Concurrent downloads must be between 1 and 20")
        return v


def load_config() -> TransFlowConfig:
    """Load configuration from environment and .env file."""
    return TransFlowConfig()
