"""Tests for logger utility.

Following Google Python testing guidelines.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from transflow.utils.logger import TransFlowLogger


class TestTransFlowLogger:
    """Tests for TransFlowLogger class."""

    def teardown_method(self) -> None:
        """Reset logger after each test to avoid state leakage."""
        TransFlowLogger.reset()

    def test_get_logger_returns_logger_instance(self) -> None:
        """Test get_logger returns a valid logging.Logger instance."""
        # Act
        logger = TransFlowLogger.get_logger()

        # Assert
        assert isinstance(logger, logging.Logger)
        assert logger.name == "transflow"

    def test_get_logger_sets_log_level(self) -> None:
        """Test get_logger sets the specified log level."""
        # Act
        logger = TransFlowLogger.get_logger(level="DEBUG")

        # Assert
        assert logger.level == logging.DEBUG

    def test_get_logger_is_singleton(self) -> None:
        """Test get_logger returns the same instance on multiple calls."""
        # Act
        logger1 = TransFlowLogger.get_logger()
        logger2 = TransFlowLogger.get_logger()

        # Assert
        assert logger1 is logger2

    def test_get_logger_adds_console_handler(self) -> None:
        """Test get_logger configures console handler."""
        # Act
        logger = TransFlowLogger.get_logger()

        # Assert
        assert len(logger.handlers) >= 1
        # RichHandler should be present
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "RichHandler" in handler_types

    def test_get_logger_adds_file_handler_when_specified(self) -> None:
        """Test get_logger adds file handler when log_file is provided."""
        # Arrange
        log_file = Path("/tmp/test.log")

        # Act
        with patch.object(Path, "mkdir"):
            with patch("logging.FileHandler") as mock_file_handler:
                logger = TransFlowLogger.get_logger(log_file=log_file)

        # Assert
        mock_file_handler.assert_called_once()

    def test_reset_clears_singleton_instance(self) -> None:
        """Test reset() clears the singleton instance."""
        # Arrange
        TransFlowLogger.get_logger()
        
        # Verify instance exists
        assert TransFlowLogger._instance is not None

        # Act
        TransFlowLogger.reset()

        # Assert
        assert TransFlowLogger._instance is None

    def test_reset_closes_handlers(self) -> None:
        """Test reset() properly closes all handlers."""
        # Arrange
        logger = TransFlowLogger.get_logger()
        handlers = logger.handlers[:]

        # Act
        with patch.object(logging.Handler, "close") as mock_close:
            TransFlowLogger.reset()

        # Assert - close should be called for each handler
        assert mock_close.call_count >= len(handlers)
