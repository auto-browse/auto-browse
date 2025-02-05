"""Browser state management using Playwright directly"""
import asyncio
import base64
import logging
from typing import List, Optional

from playwright.async_api import Page

from browser_capture.service import DomService
from browser_state.models import BrowserState, TabInfo, ViewportState

logger = logging.getLogger(__name__)

class StateManager:
    """Manages browser state using Playwright directly"""

    def __init__(self, page: Page):
        """Initialize with a Playwright page"""
        self.page = page
        self.dom_service = DomService(page)

    async def get_viewport_state(self) -> ViewportState:
        """Get current viewport state"""
        try:
            metrics = await self.page.evaluate("""() => {
                const docHeight = Math.max(
                    document.body.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.clientHeight,
                    document.documentElement.scrollHeight,
                    document.documentElement.offsetHeight
                );
                const viewportHeight = window.innerHeight;
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

                return {
                    scrollTop,
                    docHeight,
                    viewportHeight,
                    viewportWidth: window.innerWidth
                };
            }""")

            return ViewportState(
                pixels_above=metrics['scrollTop'],
                pixels_below=metrics['docHeight'] - metrics['viewportHeight'] - metrics['scrollTop'],
                width=metrics['viewportWidth'],
                height=metrics['viewportHeight']
            )
        except Exception as e:
            logger.error(f'Failed to get viewport state: {str(e)}')
            return ViewportState()

    async def get_tabs_info(self) -> List[TabInfo]:
        """Get information about all open tabs"""
        tabs = []
        context = self.page.context
        for i, page in enumerate(context.pages):
            try:
                tabs.append(TabInfo(
                    page_id=i,
                    url=page.url,
                    title=await page.title()
                ))
            except Exception as e:
                logger.error(f'Failed to get tab info: {str(e)}')
        return tabs

    async def take_screenshot(self) -> Optional[str]:
        """Take a screenshot and return as base64"""
        try:
            screenshot = await self.page.screenshot(
                animations='disabled',
            )
            return base64.b64encode(screenshot).decode('utf-8')
        except Exception as e:
            logger.error(f'Failed to take screenshot: {str(e)}')
            return None

    async def capture_state(self, include_screenshot: bool = False) -> BrowserState:
        """Capture complete browser state"""
        # Wait for network activity to settle
        try:
            await self.page.wait_for_load_state('networkidle', timeout=5000)
        except Exception:
            # Continue even if timeout occurs
            pass

        # Get DOM state with clickable elements
        dom_state = await self.dom_service.get_clickable_elements(
            highlight_elements=True,
            viewport_expansion=500
        )

        # Get viewport info
        viewport = await self.get_viewport_state()

        # Get tabs info
        tabs = await self.get_tabs_info()

        # Take screenshot if requested
        screenshot = await self.take_screenshot() if include_screenshot else None

        return BrowserState(
            url=self.page.url,
            title=await self.page.title(),
            dom_tree=dom_state.element_tree,
            selector_map=dom_state.selector_map,
            tabs=tabs,
            viewport=viewport,
            screenshot=screenshot
        )
