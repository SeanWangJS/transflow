"""Logging utilities for TransFlow."""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


class TransFlowLogger:
    """Centralized logger for TransFlow application."""

    _instance: Optional[logging.Logger] = None

    @classmethod
    def get_logger(
        cls,
        name: str = "transflow",
        level: str = "INFO",
        log_file: Optional[Path] = None,
    ) -> logging.Logger:
        """
        Get or create the application logger.

        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file path for logging

        Returns:
            Configured logger instance
        """
        if cls._instance is not None:
            return cls._instance

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # Console handler with Rich formatting
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        console_handler.setLevel(getattr(logging, level.upper()))
        console_formatter = logging.Formatter("%(message)s", datefmt="[%X]")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        cls._instance = logger
        return logger

    @classmethod
    def reset(cls) -> None:
        """Reset the logger instance (useful for testing)."""
        if cls._instance:
            for handler in cls._instance.handlers[:]:
                handler.close()
                cls._instance.removeHandler(handler)
            cls._instance = None
