"""Interactive configuration wizard for first-time setup."""

import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


class ConfigWizard:
    """Interactive wizard to help users configure TransFlow."""

    @staticmethod
    def get_config_dir() -> Path:
        """Get user config directory (~/.config/transflow)."""
        if os.name == "nt":  # Windows
            config_dir = Path.home() / "AppData" / "Local" / "transflow"
        else:  # Unix-like
            config_dir = Path.home() / ".config" / "transflow"
        
        return config_dir

    @staticmethod
    def get_env_file_path() -> Path:
        """Get .env file path in current directory."""
        return Path.cwd() / ".env"

    @classmethod
    def run(cls) -> None:
        """Run the interactive configuration wizard."""
        console.print("\n[bold cyan]TransFlow Configuration Wizard[/bold cyan]\n")
        console.print("This wizard will help you set up API keys and preferences.\n")

        # Ask for storage location
        console.print("[yellow]Where would you like to store your configuration?[/yellow]")
        console.print("1. Current directory (.env file) - for this project only")
        console.print("2. User home directory (~/.config/transflow/config) - for all projects")
        
        choice = Prompt.ask("Choose", choices=["1", "2"], default="1")
        
        if choice == "1":
            cls._setup_env_file()
        else:
            cls._setup_user_config()
        
        console.print("\n[green]✓[/green] Configuration saved successfully!\n")

    @classmethod
    def _setup_env_file(cls) -> None:
        """Set up .env file in current directory."""
        env_path = cls.get_env_file_path()
        
        console.print(f"\n[bold]Setting up .env file at:[/bold] {env_path}\n")
        
        # Collect API keys
        firecrawl_key = Prompt.ask(
            "[yellow]Firecrawl API Key[/yellow] (leave blank to skip)",
            default=""
        )
        
        openai_key = Prompt.ask(
            "[yellow]OpenAI API Key[/yellow] (leave blank to skip)",
            default=""
        )
        
        openai_base_url = Prompt.ask(
            "[yellow]OpenAI Base URL[/yellow] (for custom servers like Ollama, localai, etc.)",
            default="https://api.openai.com/v1"
        )
        
        # Collect optional settings
        model = Prompt.ask(
            "[yellow]Default Model[/yellow]",
            default="gpt-4o"
        )
        
        language = Prompt.ask(
            "[yellow]Default Language[/yellow]",
            default="zh"
        )
        
        log_level = Prompt.ask(
            "[yellow]Log Level[/yellow]",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO"
        )
        
        # Build .env content
        content = cls._build_env_content(firecrawl_key, openai_key, openai_base_url, model, language, log_level)
        
        # Write file
        env_path.write_text(content, encoding="utf-8")
        console.print(f"\n[green]✓[/green] .env file created at: [cyan]{env_path}[/cyan]")

    @classmethod
    def _setup_user_config(cls) -> None:
        """Set up configuration in user home directory."""
        config_dir = cls.get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = config_dir / "config"
        
        console.print(f"\n[bold]Setting up config file at:[/bold] {config_path}\n")
        
        # Collect API keys
        firecrawl_key = Prompt.ask(
            "[yellow]Firecrawl API Key[/yellow] (leave blank to skip)",
            default=""
        )
        
        openai_key = Prompt.ask(
            "[yellow]OpenAI API Key[/yellow] (leave blank to skip)",
            default=""
        )
        
        openai_base_url = Prompt.ask(
            "[yellow]OpenAI Base URL[/yellow] (for custom servers like Ollama, localai, etc.)",
            default="https://api.openai.com/v1"
        )
        
        # Collect optional settings
        model = Prompt.ask(
            "[yellow]Default Model[/yellow]",
            default="gpt-4o"
        )
        
        language = Prompt.ask(
            "[yellow]Default Language[/yellow]",
            default="zh"
        )
        
        log_level = Prompt.ask(
            "[yellow]Log Level[/yellow]",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO"
        )
        
        # Build env content for source command
        content = cls._build_env_content(firecrawl_key, openai_key, openai_base_url, model, language, log_level)
        
        # Write file
        config_path.write_text(content, encoding="utf-8")
        console.print(f"\n[green]✓[/green] Config file created at: [cyan]{config_path}[/cyan]")
        
        # Show how to use it
        console.print("\n[bold]To use this configuration, add to your shell profile:[/bold]")
        console.print(f"  source {config_path}")

    @staticmethod
    def _build_env_content(
        firecrawl_key: str,
        openai_key: str,
        openai_base_url: str,
        model: str,
        language: str,
        log_level: str,
    ) -> str:
        """Build .env file content."""
        lines = [
            "# TransFlow Configuration",
            "# Generated by 'transflow init' command\n",
        ]
        
        if firecrawl_key:
            lines.append(f"TRANSFLOW_FIRECRAWL_API_KEY={firecrawl_key}")
        else:
            lines.append("# TRANSFLOW_FIRECRAWL_API_KEY=your_key_here")
        
        if openai_key:
            lines.append(f"TRANSFLOW_OPENAI_API_KEY={openai_key}")
        else:
            lines.append("# TRANSFLOW_OPENAI_API_KEY=your_key_here")
        
        # Always add base_url (either custom or default)
        lines.append(f"TRANSFLOW_OPENAI_BASE_URL={openai_base_url}")
        
        lines.extend([
            f"TRANSFLOW_OPENAI_MODEL={model}",
            f"TRANSFLOW_DEFAULT_LANGUAGE={language}",
            f"TRANSFLOW_LOG_LEVEL={log_level}",
            "",
            "# Optional settings",
            "# TRANSFLOW_HTTP_TIMEOUT=30",
            "# TRANSFLOW_HTTP_MAX_RETRIES=3",
            "# TRANSFLOW_HTTP_CONCURRENT_DOWNLOADS=5",
        ])
        
        return "\n".join(lines)
