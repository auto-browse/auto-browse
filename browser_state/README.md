# browser-state

Browser state management using Playwright directly.

## Overview

This module provides state management utilities for browser automation using Playwright directly, without dependency on browser_init. It handles:

- Complete browser state tracking
- DOM tree analysis (using browser-capture)
- Tab management
- Viewport tracking
- Screenshot capture

## Installation

```bash
pip install browser-state
```

## Usage

```python
from playwright.async_api import async_playwright
from browser_state.manager import StateManager

async def manage_browser():
    async with async_playwright() as p:
        # Launch browser and create page
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Initialize state manager
        state_manager = StateManager(page)

        # Navigate to a page
        await page.goto("https://example.com")

        # Capture complete state with screenshot
        state = await state_manager.capture_state(include_screenshot=True)

        # Access state information
        print(f"Current URL: {state.url}")
        print(f"Page Title: {state.title}")
        print(f"Interactive Elements: {len(state.selector_map)}")
        print(f"Open Tabs: {len(state.tabs)}")
        print(f"Viewport Height: {state.viewport.height}")
        print(f"Screenshot Size: {len(state.screenshot) if state.screenshot else 0}")

        await browser.close()

# Run with asyncio
import asyncio
asyncio.run(manage_browser())
```

## Features

- Direct Playwright integration
- Complete state management
- DOM tree analysis
- Tab tracking
- Viewport metrics
- Screenshot capture
- Extensive test coverage

## Development

```bash
# Install dependencies and setup
pip install -e ".[test]"
python -m playwright install chromium

# Run tests
pytest

# Run linters
ruff check .
black .
mypy .
```

## Dependencies

- playwright>=1.40.0
- browser-capture>=0.1.0 (for DOM tree analysis)
- pydantic>=2.0.0
- typing-extensions>=4.0.0
- loguru>=0.7.0

## License

MIT License
