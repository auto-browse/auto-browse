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