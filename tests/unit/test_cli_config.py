"""Tests for config command in CLI."""

from typer.testing import CliRunner

from transflow.cli import app

runner = CliRunner()


class TestConfigCommand:
    """Test config command."""

    def test_config_show(self):
        """Test config show command."""
        result = runner.invoke(app, ["config", "--show"])
        assert result.exit_code == 0
        assert "TransFlow Configuration" in result.stdout or "Configuration" in result.stdout
        assert "openai_api_key" in result.stdout or "API" in result.stdout

    def test_config_validate(self):
        """Test config validate command."""
        result = runner.invoke(app, ["config", "--validate"])
        # Should exit with 0 or 1 depending on config validity
        assert result.exit_code in [0, 1]
        assert "Configuration Validation" in result.stdout or "Validation" in result.stdout

    def test_config_default_shows_config(self):
        """Test config command without arguments shows config."""
        result = runner.invoke(app, ["config"])
        # Default action is to show config
        assert result.exit_code == 0
        assert "Configuration" in result.stdout or "openai" in result.stdout.lower()

    def test_config_help(self):
        """Test config help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.stdout.lower() or "Show" in result.stdout
        assert "validate" in result.stdout.lower() or "Validate" in result.stdout


class TestConfigIntegration:
    """Integration tests for config command."""

    def test_config_show_includes_all_categories(self):
        """Test that config show includes all configuration categories."""
        result = runner.invoke(app, ["config", "--show"])
        assert result.exit_code == 0
        # Check for at least one item from each category
        # (exact output format depends on Rich table rendering)
        categories = [
            "API",
            "Extraction",
            "HTTP",
            "Logging",
        ]
        output = result.stdout.lower()
        for category in categories:
            assert category.lower() in output

    def test_config_show_has_status_indicators(self):
        """Test that config show includes status indicators."""
        result = runner.invoke(app, ["config", "--show"])
        assert result.exit_code == 0
        # Status indicators: [SET], [OPTIONAL], [MISSING]
        output = result.stdout
        has_status = (
            "[SET]" in output
            or "[OPTIONAL]" in output
            or "[MISSING]" in output
            or "SET" in output
            or "OPTIONAL" in output
            or "MISSING" in output
        )
        assert has_status

    def test_config_show_masks_api_keys(self):
        """Test that config show masks API keys."""
        # This test ensures that API keys are not shown in plain text
        result = runner.invoke(app, ["config", "--show"])
        assert result.exit_code == 0
        # API keys should be masked or hidden
        # They should not contain full "sk_test_" or "sk_live_" prefixes followed by full keys
        output = result.stdout
        # Very basic check: if there's an API key shown, it should be masked
        # (This is a basic check since we don't know the actual key value)
        if "sk_" in output or "api_key" in output.lower():
            # If API key content is shown, it should have *** (masking indicator)
            # or be [NOT SET] or similar
            assert "***" in output or "NOT SET" in output or "MISSING" in output
