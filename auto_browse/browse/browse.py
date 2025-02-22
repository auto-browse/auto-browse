import logging
from dataclasses import dataclass
from typing import Optional, Union, Literal

from auto_browse.telemetry import log_event
from browser_init.browser import Browser, BrowserConfig
from browser_init.context import BrowserContext, BrowserContextConfig
from browser_state.manager import StateManager


logger = logging.getLogger(__name__)

@dataclass
class AutoBrowseSession:
    """Session container for AutoBrowse"""
    context: BrowserContext
    state_manager: StateManager
    model: str

class AutoBrowse:
    DEFAULT_MODEL = "openai:gpt-4o-mini"

    def __init__(self, model: Union[str, None] = None, browser: Optional[Browser] = None,
                 new_context_config: Optional[BrowserContextConfig] = None, **kwargs):
        if browser is None:
            browser_config = BrowserConfig(**kwargs)
            self.browser = Browser(browser_config)
        else:
            self.browser = browser
        self.model = model if model is not None else self.DEFAULT_MODEL
        self.new_context_config = new_context_config
        self._session: Optional[AutoBrowseSession] = None

    async def get_session(self) -> AutoBrowseSession:
        """Lazy initialization of browser session"""
        if self._session is None:
            config = self.new_context_config if self.new_context_config else BrowserContextConfig()
            context = await self.browser.new_context(config)
            page = await context.get_current_page()
            state_manager = StateManager(page)
            self._session = AutoBrowseSession(
                context=context,
                state_manager=state_manager,
                model=self.model
            )
        return self._session

    async def get_current_page(self):
        """Get the current page from the session"""
        session = await self.get_session()
        return await session.context.get_current_page()

    async def get_state(self, use_vision=True):
        """Get current browser state"""
        try:
            session = await self.get_session()
            if not session or not session.context:
                raise RuntimeError("Failed to initialize browser session")

            page = await session.context.get_current_page()
            if not page:
                raise RuntimeError("Failed to get current page")

            session.state_manager = StateManager(page)  # Update state manager with current page
            state = await session.state_manager.capture_state(include_screenshot=use_vision)
            if not state:
                raise RuntimeError("Failed to capture browser state")

            return state
        except Exception as e:
            logger.error(f"Failed to get browser state: {e}")
            raise RuntimeError(f"Failed to get browser state: {e}") from e

    async def ai(self, task: str):
        """Execute AI prompt"""
        from auto_browse.agents.action import action
        from auto_browse.dependencies.common_dependencies import AgentDeps

        logger.info(f"Executing AI task: {task}")

        try:
            session = await self.get_session()
            if not session or not session.context:
                raise RuntimeError("Failed to initialize browser session")

            current_state = await self.get_state(use_vision=False)
            if not current_state:
                raise RuntimeError("Failed to get browser state")

            # Update cached state so tools use same state as AI
            browser_session = await session.context.get_session()
            if browser_session:
                browser_session.cached_state = current_state

            deps = AgentDeps(
                max_actions_per_step=4,
                browser_context=session.context,  # We've already checked session and context are not None
                state=current_state
            )

            # Cast model to KnownModelName since we know it's one of the valid values
            result = await action.run(task, deps=deps, model=session.model)  # type: ignore

            # Log AI method usage with simple success/fail status
            log_event('ai_method_called', {
                'status': 'fail' if result is None else 'success',
                'model': session.model
            })

            return result
        except Exception as e:
            logger.error(f"Failed to execute AI task: {e}")
            raise RuntimeError(f"Failed to execute AI task: {e}") from e

    async def close(self):
        """Close browser and cleanup resources"""
        if self._session:
            await self._session.context.close()
            self._session = None
        if self.browser:
            await self.browser.close()

    # Maintain async context manager support for backward compatibility
    async def __aenter__(self):
        """Async context manager entry"""
        await self.get_session()  # Ensure session is initialized
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    # Maintain explicit setup/teardown for backward compatibility
    async def setup(self):
        """Explicit async setup that can be awaited directly."""
        await self.get_session()  # Initialize session
        return self

    async def teardown(self):
        """Explicit async teardown that should be called after setup."""
        await self.close()
