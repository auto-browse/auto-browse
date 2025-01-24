# auto-browse

A Python package for AI-powered Test automation using Playwright.

## Installation

With pip:
```bash
pip install auto-browse
```

Install playwright:
```bash
playwright install --with-deps
```

Add your API keys to your `.env` file:
```bash
OPENAI_API_KEY=your_api_key_here
GEMINI_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_api_key_here
```

Set the following environment variables:
```bash
ANONYMIZED_TELEMETRY=false
BROWSER_USE_LOGGING_LEVEL=info
```
## Features

- AI-powered browser automation
- Supports OpenAI, Gemini, Ollama, Groq, Mistral, Anthropic Claude
- Built on top of Playwright
- Support for common browser actions like:
  - Google search
  - Navigation
  - Clicking elements
  - Form input
  - Tab management
  - Content extraction
  - Scrolling
  - Keyboard input
  - Dropdown interaction

## Usage

```python
import asyncio
from playwright.async_api import async_playwright
from browser_use.browser.browser import Browser, BrowserConfig
from auto_browse.browse.browse import AutoBrowse

async def main():
    async with async_playwright() as p:
        browser = Browser(config=BrowserConfig(headless=False))
        # To use other models, replace the model name with the desired model
        # e.g., "openai:gpt-4o-mini", "ollama:llama3.1", "google-gla:gemini-1.5-flash", groq:gemma2-9b-it, mistral:mistral-large-latest
        auto_browse = AutoBrowse(browser=browser, model="openai:gpt-4o-mini")
        page = await auto_browse.get_current_page()
        await asyncio.sleep(1)

        # This can run one specific step, not like two steps combined
        await auto_browse.ai("Search for 'Python automation' on Google")
        await auto_browse.ai("Click on the first search result")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

Save the above code in a file (e.g., `example.py`) and run it:

```bash
python example.py
```

### Jupyter Notebook Usage

You can also use auto-browse in a Jupyter notebook:

```python
# Cell 1: Setup
import nest_asyncio
import asyncio
nest_asyncio.apply()

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig
from auto_browse.browse.browse import AutoBrowse

browser = Browser(config=BrowserConfig(headless=False))
auto_browse = AutoBrowse(browser=browser, model="openai:gpt-4o-mini")
page = await auto_browse.get_current_page()
await asyncio.sleep(1)

# Cell 2: Search
await auto_browse.ai("Search for 'Python automation' on Google")

# Cell 3: Click result
await auto_browse.ai("Click on the first search result")

# Cell 4: Cleanup
await browser.close()
```

## Requirements

- Python 3.11+
- Playwright
- browser-use
- Other dependencies as specified in pyproject.toml

## License

MIT License