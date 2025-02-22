"""
Playwright browser initialization and basic control.
"""
import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, TypedDict

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import BrowserContext as PlaywrightBrowserContext
from playwright.async_api import Page

from browser_init.views import BrowserError, URLNotAllowedError
from browser_state.models import BrowserState
from browser_capture.views import DOMElementNode, DOMState

if TYPE_CHECKING:
    from browser_init.browser import Browser

logger = logging.getLogger(__name__)

class BrowserContextWindowSize(TypedDict):
    width: int
    height: int

DEFAULT_WINDOW_SIZE: BrowserContextWindowSize = {
    'width': 1280,
    'height': 1100
}

@dataclass
class BrowserContextConfig:
    """
    Configuration for the BrowserContext.

    Default values:
    cookies_file: None
        Path to cookies file for persistence

    disable_security: False
        Disable browser security features

    browser_window_size: {
        'width': 1280,
        'height': 1100,
    }
        Default browser window size

    no_viewport: False
        Disable viewport

    save_recording_path: None
        Path to save video recordings

    trace_path: None
        Path to save trace files. It will auto name the file with the TRACE_PATH/{context_id}.zip

    locale: None
        Specify user locale, for example en-GB, de-DE, etc. Locale will affect navigator.language value,
        Accept-Language request header value as well as number and date formatting rules.
        If not provided, defaults to the system default locale.

    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'
        custom user agent to use.

    allowed_domains: None
        List of allowed domains that can be accessed. If None, all domains are allowed.
        Example: ['example.com', 'api.example.com']
    """
    cookies_file: str | None = None
    disable_security: bool = False
    browser_window_size: BrowserContextWindowSize = field(default_factory=lambda: DEFAULT_WINDOW_SIZE)
    no_viewport: bool | None = None
    save_recording_path: str | None = None
    trace_path: str | None = None
    locale: str | None = None
    user_agent: str = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
    )
    allowed_domains: list[str] | None = None

@dataclass
class BrowserSession:
    """Browser session information"""
    context: PlaywrightBrowserContext
    current_page: Page
    cached_state: Optional['BrowserState'] = None

class BrowserContext:
    """Browser context management"""

    def __init__(
        self,
        browser: 'Browser',
        config: BrowserContextConfig = BrowserContextConfig(),
    ):
        self.context_id = str(uuid.uuid4())
        logger.debug(f'Initializing new browser context with id: {self.context_id}')

        self.config = config
        self.browser = browser
        self.session: BrowserSession | None = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._initialize_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def close(self):
        """Close the browser instance"""
        logger.debug('Closing browser context')

        try:
            if self.session is None:
                return

            await self.save_cookies()

            if self.config.trace_path:
                try:
                    await self.session.context.tracing.stop(
                        path=os.path.join(self.config.trace_path, f'{self.context_id}.zip')
                    )
                except Exception as e:
                    logger.debug(f'Failed to stop tracing: {e}')

            try:
                await self.session.context.close()
            except Exception as e:
                logger.debug(f'Failed to close context: {e}')
            finally:
                self.session = None
        except Exception as e:
            logger.error(f'Error during context close: {str(e)}')

    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.session is not None:
            logger.debug('BrowserContext was not properly closed before destruction')
            try:
                # Use sync Playwright method for force cleanup
                if hasattr(self.session.context, '_impl_obj'):
                    asyncio.run(self.session.context._impl_obj.close())
                self.session = None
            except Exception as e:
                logger.warning(f'Failed to force close browser context: {e}')

    async def _initialize_session(self):
        """Initialize the browser session"""
        logger.debug('Initializing browser context')

        playwright_browser = await self.browser.get_playwright_browser()
        context = await self._create_context(playwright_browser)
        page = await context.new_page()

        # Initialize with empty state
        from browser_state.manager import StateManager
        state_manager = StateManager(page)
        initial_state = await state_manager.capture_state()

        self.session = BrowserSession(
            context=context,
            current_page=page,
            cached_state=initial_state
        )
        return self.session

    async def get_state(self, use_vision: bool = False) -> BrowserState:
        """Get the current state of the browser, updating the cache"""
        page = await self.get_current_page()

        # Create state manager and capture state
        from browser_state.manager import StateManager
        state_manager = StateManager(page)
        new_state = await state_manager.capture_state(include_screenshot=use_vision)

        # Update cached state in session
        if self.session:
            self.session.cached_state = new_state

        return new_state

    async def get_session(self) -> BrowserSession:
        """Lazy initialization of the browser and related components"""
        if self.session is None:
            return await self._initialize_session()
        return self.session

    async def get_current_page(self) -> Page:
        """Get the current page"""
        session = await self.get_session()
        return session.current_page

    async def _create_context(self, browser: PlaywrightBrowser):
        """Creates a new browser context with anti-detection measures and loads cookies if available."""
        if self.browser.config.cdp_url and len(browser.contexts) > 0:
            context = browser.contexts[0]
        elif self.browser.config.chrome_instance_path and len(browser.contexts) > 0:
            # Connect to existing Chrome instance instead of creating new one
            context = browser.contexts[0]
        else:
            # Original code for creating new context
            context = await browser.new_context(
                viewport=self.config.browser_window_size,
                no_viewport=False,
                user_agent=self.config.user_agent,
                java_script_enabled=True,
                bypass_csp=self.config.disable_security,
                ignore_https_errors=self.config.disable_security,
                record_video_dir=self.config.save_recording_path,
                record_video_size=self.config.browser_window_size,
                locale=self.config.locale,
            )

        if self.config.trace_path:
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)

        # Load cookies if they exist
        if self.config.cookies_file and os.path.exists(self.config.cookies_file):
            with open(self.config.cookies_file, 'r') as f:
                cookies = json.load(f)
            logger.info(f'Loaded {len(cookies)} cookies from {self.config.cookies_file}')
            await context.add_cookies(cookies)

        # Expose anti-detection scripts
        await context.add_init_script(
            """
            // Webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US']
            });

            // Plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Chrome runtime
            window.chrome = { runtime: {} };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );

            // Shadow DOM
            (function () {
                const originalAttachShadow = Element.prototype.attachShadow;
                Element.prototype.attachShadow = function attachShadow(options) {
                    return originalAttachShadow.call(this, { ...options, mode: "open" });
                };
            })();
            """
        )

        return context

    def _is_url_allowed(self, url: str) -> bool:
        """Check if a URL is allowed based on the whitelist configuration."""
        if not self.config.allowed_domains:
            return True

        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # Remove port number if present
            if ':' in domain:
                domain = domain.split(':')[0]

            # Check if domain matches any allowed domain pattern
            return any(
                domain == allowed_domain.lower() or domain.endswith('.' + allowed_domain.lower())
                for allowed_domain in self.config.allowed_domains
            )
        except Exception as e:
            logger.error(f'Error checking URL allowlist: {str(e)}')
            return False

    async def _check_and_handle_navigation(self, page: Page) -> None:
        """Check if current page URL is allowed and handle if not."""
        if not self._is_url_allowed(page.url):
            logger.warning(f'Navigation to non-allowed URL detected: {page.url}')
            try:
                await self.go_back()
            except Exception as e:
                logger.error(f'Failed to go back after detecting non-allowed URL: {str(e)}')
            raise URLNotAllowedError(f'Navigation to non-allowed URL: {page.url}')

    async def navigate_to(self, url: str):
        """Navigate to a URL"""
        if not self._is_url_allowed(url):
            raise BrowserError(f'Navigation to non-allowed URL: {url}')

        page = await self.get_current_page()
        await page.goto(url)
        await page.wait_for_load_state()

    async def refresh_page(self):
        """Refresh the current page"""
        page = await self.get_current_page()
        await page.reload()
        await page.wait_for_load_state()

    async def go_back(self):
        """Navigate back in history"""
        page = await self.get_current_page()
        try:
            await page.go_back(timeout=10, wait_until='domcontentloaded')
        except Exception as e:
            logger.debug(f'During go_back: {e}')

    async def go_forward(self):
        """Navigate forward in history"""
        page = await self.get_current_page()
        try:
            await page.go_forward(timeout=10, wait_until='domcontentloaded')
        except Exception as e:
            logger.debug(f'During go_forward: {e}')

    async def close_current_tab(self):
        """Close the current tab"""
        session = await self.get_session()
        page = session.current_page
        await page.close()

        # Switch to the first available tab if any exist
        if session.context.pages:
            session.current_page = session.context.pages[0]

    async def get_page_html(self) -> str:
        """Get the current page HTML content"""
        page = await self.get_current_page()
        return await page.content()

    async def is_file_uploader(self, element_node: DOMElementNode) -> bool:
        """Check if element is a file uploader input"""
        return (
            element_node.tag_name.lower() == "input"
            and element_node.attributes.get("type", "").lower() == "file"
        )

    async def _click_element_node(self, element_node: DOMElementNode, wait_for_navigation: bool = True) -> None:
        """Click an element and handle navigation"""
        page = await self.get_current_page()
        await page.click(f'[browser-user-highlight-id="playwright-highlight-{element_node.highlight_index}"]')
        if wait_for_navigation:
            #await page.wait_for_load_state('networkidle', timeout=5000)
            await page.wait_for_load_state()

    async def switch_to_tab(self, page_id: int) -> None:
        """Switch to a specific tab by ID"""
        session = await self.get_session()
        if page_id >= len(session.context.pages):
            raise Exception(f'Tab with id {page_id} does not exist')
        session.current_page = session.context.pages[page_id]

    async def _input_text_element_node(self, element_node: DOMElementNode, text: str) -> None:
        """Input text into an element"""
        page = await self.get_current_page()
        selector = f'[browser-user-highlight-id="playwright-highlight-{element_node.highlight_index}"]'
        await page.fill(selector, text)

    async def create_new_tab(self, url: str) -> None:
        """Create a new tab and navigate to URL"""
        session = await self.get_session()
        page = await session.context.new_page()
        session.current_page = page
        await page.goto(url)
        await page.wait_for_load_state('networkidle', timeout=5000)

    async def execute_javascript(self, script: str):
        """Execute JavaScript code on the page"""
        page = await self.get_current_page()
        return await page.evaluate(script)

    async def save_cookies(self) -> None:
        """Save cookies to file if cookies_file is specified"""
        if not self.config.cookies_file or not self.session:
            return

        try:
            cookies = await self.session.context.cookies()
            os.makedirs(os.path.dirname(self.config.cookies_file), exist_ok=True)
            with open(self.config.cookies_file, 'w') as f:
                json.dump(cookies, f)
            logger.info(f'Saved {len(cookies)} cookies to {self.config.cookies_file}')
        except Exception as e:
            logger.error(f'Failed to save cookies: {str(e)}')
