import logging
from typing import Optional, List

from auto_browse.telemetry import log_event
from browser_init.browser import Browser, BrowserConfig
from browser_init.context import BrowserContext
#from browser_capture.service import DomService
from browser_state.manager import StateManager
#from browser_state.models import BrowserState


logger = logging.getLogger(__name__)

class AutoBrowse:
    DEFAULT_MODEL = "openai:gpt-4o-mini"

    def __init__(self, model: str, **kwargs):
        browser_config = BrowserConfig(**kwargs)
        self.browser = Browser(browser_config)
        self.model = model if model is not None else self.DEFAULT_MODEL
        self.context: Optional[BrowserContext] = None
        #self.page = None
        #self.dom_service = None
        self.state_manager: Optional[StateManager] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.context = await self.browser.new_context()
        # Initialize state manager with current page
        page = await self.context.get_current_page()
        self.state_manager = StateManager(page)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.browser.close()

    # async def setup(self):
    #     """Initialize browser context and services"""
    #     if not self.context:
    #         self.context = await self.browser.new_context()
    #         self.page = await self.context.get_current_page()
    #         self.dom_service = DomService(self.page)
    #         self.state_manager = StateManager(self.page)

    #         # Initialize selector map
    #         dom_state = await self.dom_service.get_clickable_elements()
    #         await self.context.get_session() # Ensure session exists
    #         session = await self.context.get_session()
    #         session.selector_map = dom_state.selector_map

    async def setup(self):
        """Explicit async setup that can be awaited directly."""
        self.context = await self.browser.new_context()
        page = await self.context.get_current_page()
        self.state_manager = StateManager(page)
        return self

    async def teardown(self):
        """Explicit async teardown that should be called after setup."""
        await self.browser.close()

    async def get_state(self, use_vision=True):
        """Get current browser state"""
        if self.context is None:
            raise RuntimeError("Browser context not initialized. Use 'async with' pattern.")
        page = await self.context.get_current_page()
        self.state_manager = StateManager(page)  # Update state manager with current page
        return await self.state_manager.capture_state(include_screenshot=use_vision)
        #if not self.state_manager:
        #    raise RuntimeError("Browser not initialized. Call setup() first.")
        #return await self.state_manager.capture_state()

    async def ai(self, task: str):
        """Execute AI prompt"""
        from auto_browse.agents.action import action
        from auto_browse.dependencies.common_dependencies import AgentDeps

        #if not self.context or not self.dom_service:
        #    await self.setup()

        #logger.info(f"Executing AI task at the context level: {task}")
        #state = await self.get_state(use_vision=True)

        # Update selector map before executing task
        #if self.dom_service and self.context:
        #    dom_state = await self.dom_service.get_clickable_elements()
        #    session = await self.context.get_session()
        #    session.selector_map = dom_state.selector_map

        logger.info(f"Executing AI task: {task}")

        if self.context is None:
            raise RuntimeError("Browser context not initialized. Use 'async with' pattern.")

        # Get session to access cached state
        #session = await self.context.get_session()
        # Get current state using state manager
        #current_state = await self.get_state(use_vision=False)
        # Use the already cached state if it exists, otherwise get fresh state
        #current_state = session.cached_state or await self.get_state(use_vision=False)

         # Always get fresh state with current DOM tree and selector map
        current_state = await self.get_state(use_vision=False)

        # Update cached state so tools use same state as AI
        session = await self.context.get_session()
        session.cached_state = current_state
        deps = AgentDeps(max_actions_per_step=4, browser_context=self.context, state=current_state)
        result = await action.run(task, deps=deps, model=self.model)

        # Log AI method usage with simple success/fail status
        log_event('ai_method_called', {
            'status': 'fail' if result is None else 'success',
            'model': self.model  # Log the model name string
        })

        return result

    async def close(self):
        """Close browser and cleanup resources"""
        if self.browser:
            await self.browser.close()
            self.context = None
            self.page = None
            self.dom_service = None
            self.state_manager = None
