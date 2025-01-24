from dataclasses import dataclass
from typing import Optional

from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext
from browser_use.browser.views import BrowserState

@dataclass
class ActionDeps:
    max_actions_per_step: int = 5  # Set a default value
    browser: Optional[Browser] = None
    browser_context: Optional[BrowserContext] = None

    def get_browser(self, browser: Browser | None = None, browser_context: BrowserContext | None = None):
        # Initialize browser first if needed
        self.browser = browser if browser is not None else (None if browser_context else Browser())

        # Initialize browser context
        if browser_context:
            self.browser_context = browser_context
        elif self.browser:
            self.browser_context = BrowserContext(
                browser=self.browser, config=self.browser.config.new_context_config
            )
        else:
            # If neither is provided, create both new
            self.browser = Browser()
            self.browser_context = BrowserContext(browser=self.browser)
        return self.browser_context

    async def get_browser_state(self):
        return await self.get_browser().get_state(use_vision=True)


@dataclass
class AgentDeps:
    max_actions_per_step: int = 5  # Set a default value
    browser_context: Optional[BrowserContext] = None
    state: Optional[BrowserState] = None
    tools_schema: Optional[str] = None
    extracted_content: Optional[str] = None
