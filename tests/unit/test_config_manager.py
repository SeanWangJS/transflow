"""Tests for config manager module."""

import os
import pytest

from transflow.config_manager import (
    ConfigItem,
    ConfigSource,
    get_config_items,
    validate_config,
)


class TestConfigItem:
    """Test ConfigItem class."""

    def test_config_item_creation(self):
        """Test creating a config item."""
        item = ConfigItem(
            key="test_key",
            value="test_value",
            source=ConfigSource.ENVIRONMENT,
            category="Test",
            description="Test description",
            required=True,
        )
        assert item.key == "test_key"
        assert item.value == "test_value"
        assert item.source == ConfigSource.ENVIRONMENT

    def test_api_key_masking(self):
        """Test API key value masking."""
        item = ConfigItem(
            key="openai_api_key",
            value="sk_test_1234567890abcdefghij",
            source=ConfigSource.ENVIRONMENT,
        )
        display = item.display_value()
        assert display.startswith("sk_te")
        assert display.endswith("ghij")
        assert "***" in display

    def test_api_key_short_masking(self):
        """Test API key masking for short keys."""
        item = ConfigItem(
            key="openai_api_key",
            value="short",
            source=ConfigSource.ENVIRONMENT,
        )
        assert item.display_value() == "****"

    def test_none_value_display(self):
        """Test display of None value."""
        item = ConfigItem(
            key="test_key",
            value=None,
            source=ConfigSource.NOT_SET,
        )
        assert item.display_value() == "[NOT SET]"

    def test_empty_string_display(self):
        """Test display of empty string."""
        item = ConfigItem(
            key="test_key",
            value="",
            source=ConfigSource.NOT_SET,
        )
        assert item.display_value() == "[NOT SET]"

    def test_source_display_environment(self):
        """Test source display for environment variables."""
        item = ConfigItem(
            key="test_key",
            value="test",
            source=ConfigSource.ENVIRONMENT,
        )
        assert "TRANSFLOW_TEST_KEY" in item.source_display()

    def test_source_display_default(self):
        """Test source display for default values."""
        item = ConfigItem(
            key="test_key",
            value="default_value",
            source=ConfigSource.DEFAULT,
        )
        assert "(default)" in item.source_display()

    def test_status_display_set(self):
        """Test status display for set values."""
        item = ConfigItem(
            key="test_key",
            value="test_value",
            source=ConfigSource.ENVIRONMENT,
            required=True,
        )
        assert "[SET]" in item.status_display()

    def test_status_display_missing_required(self):
        """Test status display for missing required value."""
        item = ConfigItem(
            key="test_key",
            value=None,
            source=ConfigSource.NOT_SET,
            required=True,
        )
        assert "[MISSING]" in item.status_display()

    def test_status_display_optional(self):
        """Test status display for optional missing value."""
        item = ConfigItem(
            key="test_key",
            value=None,
            source=ConfigSource.NOT_SET,
            required=False,
        )
        assert "[OPTIONAL]" in item.status_display()


class TestGetConfigItems:
    """Test get_config_items function."""

    def test_get_config_items_structure(self):
        """Test that get_config_items returns expected structure."""
        items = get_config_items()
        assert isinstance(items, dict)
        assert len(items) > 0

    def test_get_config_items_categories(self):
        """Test that all expected categories are present."""
        items = get_config_items()
        expected_categories = [
            "API Configuration",
            "Extraction Configuration",
            "HTTP Configuration",
            "Logging Configuration",
            "Default Language",
        ]
        for category in expected_categories:
            assert category in items

    def test_config_items_have_descriptions(self):
        """Test that all config items have descriptions."""
        items = get_config_items()
        for category, config_items in items.items():
            for item in config_items:
                assert item.description, f"Missing description for {item.key}"

    def test_config_items_required_status(self):
        """Test that required status is set appropriately."""
        items = get_config_items()
        api_config = items["API Configuration"]

        # openai_api_key should be required
        api_key_item = next(
            (item for item in api_config if item.key == "openai_api_key"), None
        )
        assert api_key_item is not None
        assert api_key_item.required is True

        # openai_model should be optional
        model_item = next(
            (item for item in api_config if item.key == "openai_model"), None
        )
        assert model_item is not None
        assert model_item.required is False


class TestValidateConfig:
    """Test validate_config function."""

    def test_validate_config_returns_tuple(self):
        """Test that validate_config returns a tuple."""
        result = validate_config()
        assert isinstance(result, tuple)
        assert len(result) == 3
        is_valid, warnings, errors = result
        assert isinstance(is_valid, bool)
        assert isinstance(warnings, list)
        assert isinstance(errors, list)

    def test_validate_config_missing_api_key(self, monkeypatch):
        """Test validation fails when API key is missing."""
        # Clear the API key environment variable
        monkeypatch.delenv("TRANSFLOW_OPENAI_API_KEY", raising=False)

        is_valid, warnings, errors = validate_config()
        # May or may not be valid depending on implementation
        # but should have error about missing API key
        assert any("openai_api_key" in str(e).lower() for e in errors)

    def test_validate_config_invalid_log_level(self, monkeypatch):
        """Test validation fails with invalid log level."""
        monkeypatch.setenv("TRANSFLOW_LOG_LEVEL", "INVALID_LEVEL")

        is_valid, warnings, errors = validate_config()
        assert not is_valid
        assert any("log_level" in str(e).lower() for e in errors)

    def test_validate_config_negative_timeout(self, monkeypatch):
        """Test validation fails with negative timeout."""
        monkeypatch.setenv("TRANSFLOW_HTTP_TIMEOUT", "-1")

        is_valid, warnings, errors = validate_config()
        assert not is_valid
        assert any("http_timeout" in str(e).lower() for e in errors)

    def test_validate_config_missing_firecrawl_warning(self, monkeypatch):
        """Test that missing Firecrawl API key triggers warning."""
        monkeypatch.delenv("TRANSFLOW_FIRECRAWL_API_KEY", raising=False)

        is_valid, warnings, errors = validate_config()
        assert any("firecrawl" in str(w).lower() for w in warnings)

    def test_validate_config_invalid_concurrent_downloads(self, monkeypatch):
        """Test validation fails with invalid concurrent downloads count."""
        monkeypatch.setenv("TRANSFLOW_HTTP_CONCURRENT_DOWNLOADS", "50")

        is_valid, warnings, errors = validate_config()
        assert not is_valid
        assert any("concurrent_downloads" in str(e).lower() for e in errors)


class TestConfigSource:
    """Test ConfigSource enum."""

    def test_config_source_values(self):
        """Test ConfigSource enum values."""
        assert ConfigSource.ENVIRONMENT.value == "env"
        assert ConfigSource.ENV_FILE.value == ".env"
        assert ConfigSource.DEFAULT.value == "default"
        assert ConfigSource.NOT_SET.value == "not set"
