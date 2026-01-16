"""Test configuration module."""

import pytest
from pydantic import ValidationError

from transflow.config import TransFlowConfig


def test_default_config() -> None:
    """Test default configuration values."""
    config = TransFlowConfig()
    
    assert config.default_model == "gpt-4o"
    assert config.default_language == "zh"
    assert config.log_level == "INFO"
    assert config.http_timeout == 30
    assert config.http_max_retries == 3
    assert config.http_concurrent_downloads == 5


def test_config_validation_timeout() -> None:
    """Test timeout validation."""
    with pytest.raises(ValidationError):
        TransFlowConfig(http_timeout=-1)


def test_config_validation_log_level() -> None:
    """Test log level validation."""
    with pytest.raises(ValidationError):
        TransFlowConfig(log_level="INVALID")


def test_config_validation_concurrent_downloads() -> None:
    """Test concurrent downloads validation."""
    with pytest.raises(ValidationError):
        TransFlowConfig(http_concurrent_downloads=0)
    
    with pytest.raises(ValidationError):
        TransFlowConfig(http_concurrent_downloads=21)
