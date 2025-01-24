import logging

from browser_use.browser.browser import BrowserContext

logger = logging.getLogger(__name__)

class AutoBrowse(BrowserContext):
    DEFAULT_MODEL = "openai:gpt-4o-mini"

    def __init__(self, model: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model or self.DEFAULT_MODEL

    async def ai(self, task: str):
        """Execute AI prompt"""
        from auto_browse.agents.action import action
        from auto_browse.dependencies.common_dependencies import AgentDeps
        logger.info(f"Executing AI task at the context level: {task}")
        deps = AgentDeps(max_actions_per_step=4, browser_context=self, state=self.get_state(use_vision=False))
        result = await action.run(task, deps=deps, model=self.model)
        return result