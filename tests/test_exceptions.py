"""Tests for custom exceptions."""

import pytest

from transflow.exceptions import (
    APIError,
    ConfigurationError,
    TransFlowException,
    NetworkError,
    TranslationError,
    ValidationError,
)


class TestTransFlowException:
    """Tests for base TransFlowException class."""

    def test_init_with_message(self) -> None:
        """Test exception initialization with message."""
        exc = TransFlowException("Test error")
        assert str(exc) == "Test error"
        assert exc.exit_code == 1

    def test_init_with_exit_code(self) -> None:
        """Test exception initialization with custom exit code."""
        exc = TransFlowException("Test error", exit_code=2)
        assert exc.exit_code == 2


class TestNetworkError:
    """Tests for NetworkError exception."""

    def test_network_error_exit_code(self) -> None:
        """Test NetworkError has correct exit code."""
        exc = NetworkError("Connection failed")
        assert exc.exit_code == 1
        assert str(exc) == "Connection failed"


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_exit_code(self) -> None:
        """Test ValidationError has correct exit code."""
        exc = ValidationError("Invalid input")
        assert exc.exit_code == 2
        assert str(exc) == "Invalid input"


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_configuration_error_exit_code(self) -> None:
        """Test ConfigurationError has correct exit code."""
        exc = ConfigurationError("Config missing")
        assert exc.exit_code == 2
        assert str(exc) == "Config missing"


class TestAPIError:
    """Tests for APIError exception."""

    def test_api_error_default_exit_code(self) -> None:
        """Test APIError has default exit code."""
        exc = APIError("API failed")
        assert exc.exit_code == 1

    def test_api_error_custom_exit_code(self) -> None:
        """Test APIError with custom exit code."""
        exc = APIError("API failed", exit_code=2)
        assert exc.exit_code == 2


class TestTranslationError:
    """Tests for TranslationError exception."""

    def test_translation_error_exit_code(self) -> None:
        """Test TranslationError has correct exit code."""
        exc = TranslationError("Translation failed")
        assert exc.exit_code == 1
        assert str(exc) == "Translation failed"
