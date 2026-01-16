"""Configuration for integration tests with environment consistency."""

import os
from pathlib import Path

import pytest

# Load .env.test if it exists (for local development)
ENV_TEST_FILE = Path(__file__).parent.parent.parent / ".env.test"


def pytest_configure(config):
    """Register custom markers and load test environment."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    )
    
    # Load test-specific environment variables
    if ENV_TEST_FILE.exists():
        _load_env_file(ENV_TEST_FILE)


def _load_env_file(env_file: Path) -> None:
    """Load environment variables from .env file."""
    if not env_file.exists():
        return
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, value = line.partition("=")
                if key and value:
                    os.environ[key.strip()] = value.strip()
