from dataclasses import dataclass
from typing import Optional

from browser_init.browser import Browser
from browser_init.context import BrowserContext
from browser_state.models import BrowserState

@dataclass
class ActionDeps:
    max_actions_per_step: int = 5  # Set a default value
    browser: Optional[Browser] = None
    browser_context: Optional[BrowserContext] = None

    async def get_browser(self, browser: Browser | None = None, browser_context: BrowserContext | None = None):
        # Initialize browser first if needed
        self.browser = browser if browser is not None else (None if browser_context else Browser())

        # Initialize browser context
        if browser_context:
            self.browser_context = browser_context
        elif self.browser:
            self.browser_context = await self.browser.new_context()
        else:
            # If neither is provided, create both new
            self.browser = Browser()
            self.browser_context = await self.browser.new_context()
        return self.browser_context

    async def get_browser_state(self):
        from browser_state.manager import StateManager
        page = await self.browser_context.new_page()
        state_manager = StateManager(page)
        return await state_manager.capture_state()


@dataclass
class AgentDeps:
    max_actions_per_step: int = 5  # Set a default value
    browser_context: Optional[BrowserContext] = None
    state: Optional[BrowserState] = None
    tools_schema: Optional[str] = None
    extracted_content: Optional[str] = None
