# browser-capture

DOM tree building and screenshot capture utilities for browser-use.

## Overview

This package provides DOM tree processing and screenshot capture functionality. It handles:

- DOM tree construction and analysis
- Element selector mapping
- Screenshot capture and processing
- Interactive element detection
- History tree processing for state tracking

## Installation

```bash
pip install browser-capture
```

## Usage

```python
from playwright.async_api import Page, Browser, async_playwright
from browser_capture.service import DOMService
from browser_capture.views import DOMState

async def capture_page_state():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Create DOM service
        dom_service = DOMService(page)

        # Navigate to page
        await page.goto("https://example.com")

        # Get DOM state with selectors
        dom_state = await dom_service.get_clickable_elements()

        # Access processed information
        print(f"Found {len(dom_state.selector_map)} interactive elements")
        print(f"Page structure: {dom_state.element_tree}")

        # Take screenshot
        screenshot = await page.screenshot()
        print(f"Screenshot captured: {len(screenshot)} bytes")

        await browser.close()

# Run with asyncio
import asyncio
asyncio.run(capture_page_state())
```

## Features

- Comprehensive DOM tree analysis
- Efficient selector mapping
- Screenshot capture and processing
- Interactive element detection
- History tracking for state changes
- Direct Playwright integration

## Dependencies

- pydantic>=2.0.0
- typing-extensions>=4.0.0
- loguru>=0.7.0
- beautifulsoup4>=4.9.0
- lxml>=4.9.0
- Pillow>=10.0.0
- playwright>=1.40.0

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

## License

MIT License
