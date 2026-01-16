# transflow

A modular command-line interface (CLI) tool designed to transform web content into archival-quality Markdown artifacts.

## Features

- 🌐 **Download**: Fetch web content and convert to clean Markdown using Firecrawl API
- 🌍 **Translate**: AI-powered translation with structure preservation using OpenAI/LLM
- 📦 **Bundle**: Localize assets (images) and create self-contained folders
- 🔄 **Pipeline**: Run complete workflow with a single command

## Installation

```bash
pip install transflow
```

Or install from source:

```bash
git clone https://github.com/seanwang/transflow.git
cd transflow
pip install -e .
```

## Quick Start

### 1. Download web content

Fetch an article and convert it to Markdown with metadata:

```bash
transflow download https://example.com/article -o article.md
```

**Output**: `article.md` with YAML frontmatter containing source URL and fetch timestamp.

### 2. Translate to Chinese

Translate while preserving code blocks, links, and formatting:

```bash
transflow translate -i article.md -o article_zh.md --lang zh
```

**Supported languages**: `zh` (Chinese), `en` (English), `ja` (Japanese), `ko` (Korean), `fr` (French), `de` (German), `es` (Spanish)

### 3. Bundle with localized assets

Download remote images and create a self-contained folder:

```bash
transflow bundle -i article_zh.md -o ./output
```

**Output**: A folder with `README.md`, `assets/` directory, and `meta.yaml` metadata.

### 4. Or run the complete pipeline

Execute all steps in one command:

```bash
transflow run https://example.com/article -o ./output --lang zh
```

## Configuration

TransFlow provides multiple ways to configure API keys and settings:

### Quick Start: Interactive Setup

The easiest way to get started is using the interactive wizard:

```bash
transflow init
```

This command will guide you through:
- Where to store configuration (project-level or user-level)
- API keys (Firecrawl, OpenAI)
- Default preferences (model, language, log level)

### Configuration Methods (Priority Order)

1. **Command-line arguments** (highest priority)
   ```bash
   transflow download https://example.com -o article.md --verbose
   ```

2. **Environment variables** (for CI/CD, containers)
   ```bash
   export TRANSFLOW_OPENAI_API_KEY=sk-...
   export TRANSFLOW_FIRECRAWL_API_KEY=...
   transflow download https://example.com -o article.md
   ```

3. **.env file** (project-level, use `transflow init` to create)
   ```bash
   # In your project root, create .env:
   TRANSFLOW_FIRECRAWL_API_KEY=your_key
   TRANSFLOW_OPENAI_API_KEY=your_key
   ```

4. **User config** (system-wide, use `transflow init` to create)
   ```bash
   # ~/.config/transflow/config (Linux/Mac)
   # ~/AppData/Local/transflow/config (Windows)
   ```

5. **Default values** (lowest priority)

### Manual Configuration

If you prefer to set up manually, create a `.env` file:

```env
# Required: Firecrawl API (for download)
TRANSFLOW_FIRECRAWL_API_KEY=your_firecrawl_key

# Required: OpenAI API (for translate)
TRANSFLOW_OPENAI_API_KEY=your_openai_key

# Optional: Custom settings
TRANSFLOW_OPENAI_BASE_URL=https://api.openai.com/v1
TRANSFLOW_DEFAULT_MODEL=gpt-4o
TRANSFLOW_DEFAULT_LANGUAGE=zh

# Optional: Logging and HTTP
TRANSFLOW_LOG_LEVEL=INFO
TRANSFLOW_HTTP_TIMEOUT=30
TRANSFLOW_HTTP_MAX_RETRIES=3
TRANSFLOW_HTTP_CONCURRENT_DOWNLOADS=5
```

### Configuration Priority

1. Command-line arguments (highest)
2. Environment variables (`TRANSFLOW_*`)
3. `.env` file
4. Default values (lowest)

## Command Reference

### `transflow init`

Initialize configuration interactively.

```bash
transflow init
```

**What it does**:
- Prompts you for API keys and preferences
- Lets you choose between project-level or user-level storage
- Creates configuration file automatically

**Example**:
```bash
$ transflow init

TransFlow Configuration Wizard

Where would you like to store your configuration?
1. Current directory (.env file) - for this project only
2. User home directory (~/.config/transflow/config) - for all projects

Choose: 1

Setting up .env file...
Firecrawl API Key: sk-proj-xxxxx
OpenAI API Key: sk-xxxxx
Default Model [gpt-4o]: gpt-4o
Default Language [zh]: zh
Log Level [INFO]: INFO

✓ Configuration saved successfully!
```

### `transflow download`

Download and convert web content to Markdown.

```bash
transflow download <url> [options]

Options:
  -o, --output PATH    Output file path (auto-generated if omitted)
  --engine TEXT        Extraction engine [default: firecrawl]
  -v, --verbose        Enable verbose logging
```

**Example**:
```bash
transflow download https://blog.example.com/post -o blog-post.md --verbose
```

### `transflow translate`

Translate Markdown content using LLM.

```bash
transflow translate -i <input> -o <output> [options]

Options:
  -i, --input PATH     Source Markdown file (required)
  -o, --output PATH    Destination file (required)
  --lang TEXT          Target language code [default: zh]
  --model TEXT         LLM model to use [default: gpt-4o]
  -v, --verbose        Enable verbose logging
```

**Example**:
```bash
transflow translate -i article.md -o article_ja.md --lang ja --model gpt-4-turbo
```

**Translation Behavior**:
- Translates: Paragraphs, headings, list items, blockquotes
- Preserves: Code blocks, HTML blocks, URLs, image paths
- Smart batching: Optimizes API calls for efficiency

### `transflow bundle`

Localize assets and create self-contained package.

```bash
transflow bundle -i <input> -o <output> [options]

Options:
  -i, --input PATH     Markdown file to bundle (required)
  -o, --output PATH    Output directory (required)
  --folder TEXT        Folder naming pattern [default: {year}/{date}-{slug}]
  -v, --verbose        Enable verbose logging
```

**Folder Pattern Tokens**:
- `{year}` - Current year (e.g., `2026`)
- `{month}` - Month with zero-padding (e.g., `01`)
- `{day}` - Day with zero-padding (e.g., `14`)
- `{date}` - Full date `YYYYMMDD` (e.g., `20260114`)
- `{slug}` - URL-safe article title

**Example**:
```bash
transflow bundle -i article.md -o ./archives --folder "{year}/{month}/{slug}"
```

**Output Structure**:
```
archives/
└── 2026/
    └── 01/
        └── my-article/
            ├── README.md       # Main content with local image links
            ├── assets/         # Downloaded images
            |  ├── image1.png
            |  └── image2.jpg
            └── meta.yaml       # Metadata (title, source, asset list)
```

### `transflow run`

Execute full pipeline: download -> translate -> bundle.

```bash
transflow run <url> -o <output> [options]

Options:
  -o, --output PATH    Target directory (required)
  --lang TEXT          Target language [default: zh]
  -v, --verbose        Enable verbose logging
```

**Example**:
```bash
transflow run https://news.example.com/article -o ./knowledge-base --lang en
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/seanwang/transflow.git
cd transflow

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=transflow --cov-report=html

# Run linters
ruff check .
black --check .
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_extractor.py

# Run with verbose output
pytest -v

# Run only fast tests (skip slow ones)
pytest -m "not slow"
```

## Architecture

transflow follows the **Unix Philosophy**:

- **Modularity**: Each command is independent and composable
- **No Hidden State**: Everything is stored in files (no databases)
- **Single Responsibility**: Each module has one clear purpose
- **Composability**: Commands can be chained with pipes or scripts

### Project Structure

```
transflow/
├── src/transflow/
|  ├── cli.py              # CLI entry point
|  ├── config.py           # Configuration management
|  ├── exceptions.py       # Custom exceptions
|  ├── utils/              # Utility modules
|  |  ├── logger.py       # Logging setup
|  |  ├── http.py         # HTTP client with retry
|  |  └── filesystem.py   # File operations
|  └── core/               # Core business logic
|      ├── extractor.py    # Web content extraction
|      ├── llm.py          # LLM client
|      ├── translator.py   # Markdown translation
|      └── bundler.py      # Asset bundling
└── tests/                  # Unit tests (Google style)
```

## Troubleshooting

### API Key Errors

**Problem**: `Firecrawl API key is required`

**Solution**: Set environment variable:
```bash
export TRANSFLOW_FIRECRAWL_API_KEY=your_key_here
```

### Translation Failures

**Problem**: Translation times out or fails

**Solutions**:
- Increase timeout: `export TRANSFLOW_HTTP_TIMEOUT=60`
- Reduce batch size (edit `translator.py`)
- Check API quota/rate limits

### Image Download Issues

**Problem**: Some images fail to download

**Behavior**: Non-critical - bundler continues with available images

**Check**: Review logs with `--verbose` flag

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Quality Standards

- Follow Google Python testing guidelines
- Maintain >80% test coverage
- Use type hints throughout
- Format with `black` and lint with `ruff`

## License

MIT License - see [LICENSE](LICENSE) for details.

## Documentation

- [Specification](docs/Spec_v3.0.md) - Detailed technical specification
- [Development Plan](docs/Dev.md) - Implementation roadmap

## Acknowledgments

- **Firecrawl** - Web content extraction
- **OpenAI** - LLM translation services
- **Marko** - Markdown AST parsing
- **Typer** - CLI framework
- **Rich** - Terminal UI

## Version

Current version: **0.0.1** (Development)

Target release: **3.0.0**
