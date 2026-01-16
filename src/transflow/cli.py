"""CLI application with Typer."""

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from typing_extensions import Annotated

from transflow import __version__
from transflow.config import load_config
from transflow.config_manager import get_config_items, validate_config
from transflow.config_wizard import ConfigWizard
from transflow.core.bundler import AssetBundler
from transflow.core.extractor import MarkdownExtractor
from transflow.core.translator import MarkdownTranslator
from transflow.exceptions import TransFlowException
from transflow.utils.logger import TransFlowLogger

app = typer.Typer(
    name="transflow",
    help="Transform web content into archival-quality Markdown artifacts.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold cyan]TransFlow[/bold cyan] version [green]{__version__}[/green]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """
    TransFlow - A modular CLI tool for transforming web content into Markdown.
    
    Run 'transflow COMMAND --help' for more information on a command.
    """
    pass


@app.command()
def init() -> None:
    """
    Initialize TransFlow configuration interactively.
    
    This command guides you through setting up API keys and preferences.
    
    Example:
        transflow init
    """
    try:
        ConfigWizard.run()
    except Exception as e:
        console.print(f"[red]✗ Setup failed:[/red] {e}")
        sys.exit(1)


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option(
            "--show",
            help="Show current configuration",
        ),
    ] = False,
    validate: Annotated[
        bool,
        typer.Option(
            "--validate",
            help="Validate configuration",
        ),
    ] = False,
) -> None:
    """
    Manage and view TransFlow configuration.

    Use --show to display all configuration values with sources.
    Use --validate to check if configuration is correct.

    Example:
        transflow config --show
        transflow config --validate
    """
    try:
        if show:
            _show_config()
        elif validate:
            _validate_config()
        else:
            # Default: show config
            _show_config()

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)


def _show_config() -> None:
    """Display current configuration in a formatted table."""
    items = get_config_items()

    console.print("[bold cyan]TransFlow Configuration[/bold cyan]\n")

    for category, config_items in items.items():
        # Create table for each category
        table = Table(title=category, show_header=True, header_style="bold magenta")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Source", style="dim")
        table.add_column("Status", style="yellow")

        for item in config_items:
            # Determine status color
            if "[MISSING]" in item.status_display():
                status_style = "red"
            elif "[SET]" in item.status_display():
                status_style = "green"
            else:
                status_style = "yellow"

            table.add_row(
                item.key,
                item.display_value(),
                item.source_display(),
                f"[{status_style}]{item.status_display()}[/{status_style}]",
            )

        console.print(table)
        console.print()


def _validate_config() -> None:
    """Validate configuration and show issues."""
    is_valid, warnings, errors = validate_config()

    console.print("[bold cyan]Configuration Validation[/bold cyan]\n")

    if is_valid:
        console.print("[green]✓ Configuration is valid![/green]\n")
    else:
        console.print("[red]✗ Configuration has issues:[/red]\n")

    if errors:
        console.print("[bold red]Errors:[/bold red]")
        for i, error in enumerate(errors, 1):
            console.print(f"  {i}. {error}")
        console.print()

    if warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for i, warning in enumerate(warnings, 1):
            console.print(f"  {i}. {warning}")
        console.print()

    if not errors and not warnings:
        console.print("No issues found.")

    sys.exit(0 if is_valid else 1)


@app.command()
def download(
    url: Annotated[str, typer.Argument(help="The URL to fetch and convert to Markdown")],
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output filename (default: auto-generated from URL)",
        ),
    ] = "",
    engine: Annotated[
        str,
        typer.Option(
            "--engine",
            help="Extraction engine to use",
        ),
    ] = "firecrawl",
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose logging",
        ),
    ] = False,
) -> None:
    """
    Download web content and convert to clean Markdown.
    
    Example:
        transflow download https://example.com/article -o article.md
    """
    try:
        # Load configuration first to get default log level
        config = load_config()

        # Setup logging: verbose flag > env var > config default > INFO
        if verbose:
            log_level = "DEBUG"
        else:
            log_level = config.log_level
        logger = TransFlowLogger.get_logger(level=log_level)

        # Create extractor
        extractor = MarkdownExtractor(config)

        # Parse output path
        output_path = Path(output) if output else None

        # Run async fetch
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description=f"Downloading from {url}...", total=None)

            result_path = asyncio.run(extractor.fetch_and_save(url, output_path))

        console.print(f"[green]✓[/green] Successfully saved to: [cyan]{result_path}[/cyan]")

    except TransFlowException as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(e.exit_code)
    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {e}")
        logger.exception("Unexpected error during download")
        sys.exit(1)


@app.command()
def translate(
    input_file: Annotated[
        str,
        typer.Option(
            "--input",
            "-i",
            help="Source Markdown file",
        ),
    ],
    output_file: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Destination Markdown file",
        ),
    ],
    lang: Annotated[
        str,
        typer.Option(
            "--lang",
            help="Target language code (e.g., zh, en, ja)",
        ),
    ] = "zh",
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            help="LLM model to use (e.g., gpt-4o, deepseek-chat). Uses TRANSFLOW_OPENAI_MODEL if not specified.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose logging",
        ),
    ] = False,
) -> None:
    """
    Translate Markdown content while preserving structure.
    
    Example:
        transflow translate -i raw.md -o trans.md --lang zh
    """
    try:
        # Load configuration first to get default log level
        config = load_config()

        # Setup logging: verbose flag > env var > config default > INFO
        if verbose:
            log_level = "DEBUG"
        else:
            log_level = config.log_level
        logger = TransFlowLogger.get_logger(level=log_level)

        # Use provided model or fall back to config default
        effective_model = model or config.openai_model

        # Create translator
        translator = MarkdownTranslator(config, model=effective_model, target_language=lang)

        # Parse paths
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            console.print(f"[red]✗ Error:[/red] Input file not found: {input_path}")
            sys.exit(2)

        # Run translation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description=f"Translating to {lang}...", total=None)

            asyncio.run(translator.translate_file(input_path, output_path))

        console.print(f"[green]✓[/green] Translation saved to: [cyan]{output_path}[/cyan]")

    except TransFlowException as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(e.exit_code)
    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {e}")
        logger.exception("Unexpected error during translation")
        sys.exit(1)


@app.command()
def bundle(
    input_file: Annotated[
        str,
        typer.Option(
            "--input",
            "-i",
            help="The Markdown file to bundle",
        ),
    ],
    output_dir: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Target directory for bundled content",
        ),
    ],
    folder: Annotated[
        str,
        typer.Option(
            "--folder",
            help="Folder naming format (e.g., {year}/{date}-{slug})",
        ),
    ] = "{year}/{date}-{slug}",
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose logging",
        ),
    ] = False,
) -> None:
    """
    Localize assets (images) and bundle into a folder.
    
    Example:
        transflow bundle -i article.md -o ./output/articles
    """
    try:
        # Load configuration first to get default log level
        config = load_config()

        # Setup logging: verbose flag > env var > config default > INFO
        if verbose:
            log_level = "DEBUG"
        else:
            log_level = config.log_level
        logger = TransFlowLogger.get_logger(level=log_level)

        # Create bundler
        bundler = AssetBundler(config)

        # Parse paths
        input_path = Path(input_file)
        output_path = Path(output_dir)

        if not input_path.exists():
            console.print(f"[red]✗ Error:[/red] Input file not found: {input_path}")
            sys.exit(2)

        # Run bundling
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="Bundling assets...", total=None)

            result_dir = asyncio.run(bundler.bundle(input_path, output_path, folder))

        console.print(f"[green]✓[/green] Bundle created at: [cyan]{result_dir}[/cyan]")

    except TransFlowException as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(e.exit_code)
    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {e}")
        logger.exception("Unexpected error during bundling")
        sys.exit(1)


@app.command()
def run(
    url: Annotated[str, typer.Argument(help="The URL to process")],
    output_dir: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Target directory for final output",
        ),
    ],
    lang: Annotated[
        str,
        typer.Option(
            "--lang",
            help="Target language for translation",
        ),
    ] = "zh",
) -> None:
    """
    Run the complete pipeline: download → translate → bundle.
    
    Example:
        transflow run https://example.com/article -o ./output
    """
    console.print(f"[yellow]Running pipeline for:[/yellow] {url}")
    console.print(f"[yellow]Language:[/yellow] {lang}")
    console.print(f"[yellow]Output:[/yellow] {output_dir}")
    console.print("[red]Not implemented yet[/red]")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
