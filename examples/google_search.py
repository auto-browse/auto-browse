import asyncio
from playwright.async_api import Page, expect
from auto_browse.browse.browse import AutoBrowse

async def main():
    async with AutoBrowse(headless=False, model="openai:gpt-4o-mini") as auto_browse:
        # To use other models, replace the model name with the desired model
        # e.g., "openai:gpt-4o-mini", "ollama:llama3.1", "google-gla:gemini-1.5-flash", groq:gemma2-9b-it, mistral:mistral-large-latest
        page = await auto_browse.get_current_page()
        await asyncio.sleep(1)

        # This can run one specific step, not like two steps combined
        await auto_browse.ai("Search for 'Python automation' on Google")
        await asyncio.sleep(5)
        await expect(page).to_have_title("Python automation - Google Search")
        await auto_browse.ai("Click on the first search result")

        await auto_browse.ai("Search for 'Gurvinder Dhillon' on Google")
        await asyncio.sleep(5)
        await expect(page).to_have_title("Gurvinder Dhillon - Google Search")
        await auto_browse.ai("Click on the Linkedin search result of Gurvinder Dhillon")

        await auto_browse.ai("Search for 'auto-browse' on Google")
        await asyncio.sleep(5)
        await expect(page).to_have_title("auto-browse - Google Search")
        await auto_browse.ai("Click on the auto-browse.com search result")

        await auto_browse.close()

if __name__ == "__main__":
    asyncio.run(main())