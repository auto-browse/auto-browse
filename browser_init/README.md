# browser-init

Browser initialization and context management for browser-use.

## Overview

This package provides the core browser initialization and context management functionality. It handles:

- Browser instance creation and management
- Browser context setup and configuration
- State management and session handling
- Screenshot capture coordination
- Tab management

## Installation

```bash
pip install browser-init
```

## Usage

```python
from browser_init.browser import Browser
from browser_init.context import BrowserContext, BrowserContextConfig

# Initialize browser
browser = Browser()

# Create context with custom configuration
config = BrowserContextConfig(
    viewport_size={"width": 1280, "height": 720},
    use_vision=True
)
context = BrowserContext(browser=browser, config=config)

# Use the context
async with context.session() as page:
    await page.goto("https://example.com")
    state = await context.get_state()
    print(f"Current URL: {state.url}")
    print(f"Page Title: {state.title}")

# Clean up
await browser.close()
```

## Features

- Async-first design for efficient browser automation
- Flexible configuration options
- Built-in state management
- Screenshot capture support
- Multi-tab handling
- Vision mode support for visual analysis

## Dependencies

- playwright>=1.40.0
- pydantic>=2.0.0
- typing-extensions>=4.0.0
- loguru>=0.7.0

## Development

```bash
# Install development dependencies
pdm install -G test,lint

# Run tests
pytest

# Run linters
ruff check .
black .
mypy .
```

## License

MIT License
