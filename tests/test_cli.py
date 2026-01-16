"""Tests for CLI module."""

import pytest
from typer.testing import CliRunner

from transflow.cli import app


runner = CliRunner()


def test_cli_version() -> None:
    """Test CLI version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "TransFlow" in result.stdout
    assert "0.0.1" in result.stdout or "3.0.0" in result.stdout


def test_cli_help() -> None:
    """Test CLI help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Transform web content" in result.stdout or "download" in result.stdout
