"""Tests configuration and fixtures."""

import pytest


@pytest.fixture
def sample_markdown() -> str:
    """Sample Markdown content for testing."""
    return """# Test Article

This is a test paragraph with some **bold** and *italic* text.

## Code Example

```python
def hello():
    print("Hello, world!")
```

## List

- Item 1
- Item 2
- Item 3

![Test Image](https://example.com/image.png)
"""


@pytest.fixture
def sample_url() -> str:
    """Sample URL for testing."""
    return "https://example.com/article"
