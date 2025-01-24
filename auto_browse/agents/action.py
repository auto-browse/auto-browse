from dataclasses import dataclass
from datetime import datetime
import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.test import TestModel

from auto_browse.dependencies.common_dependencies import AgentDeps
from auto_browse.tools.browser_actions import (
    search_google, go_to_url, click_element, input_text, switch_tab,
    open_tab, extract_content, scroll_down, scroll_up, send_keys,
    scroll_to_text, get_dropdown_options, select_dropdown_option, go_back, done
)

from browser_use.controller.views import (
    ClickElementAction,
    DoneAction,
    ExtractPageContentAction,
    GoToUrlAction,
    InputTextAction,
    OpenTabAction,
    ScrollAction,
    SearchGoogleAction,
    SendKeysAction,
    SwitchTabAction,
)
from browser_use.agent.views import (ActionResult)

logger = logging.getLogger(__name__)

action = Agent(
    deps_type=AgentDeps
)
@action.system_prompt
async def core_instructions() -> str:
	time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
	return f"""
		You are a precise browser automation agent that interacts with websites using the tools provided to you.
		Your role is to:
		1. Analyze the provided webpage elements and structure
		2. Plan a sequence of actions to accomplish the given task
		3. Call the required tools to execute the actions
        4. You have access to current url, tabs, and interactive elements on the page to help you plan your actions
		"""

@action.system_prompt
async def browser_state_prompt(ctx: RunContext[AgentDeps]) -> str:
    #state = await ctx.deps.get_browser_state()
    attr = [
            'title',
            'type',
            'name',
            'role',
            'tabindex',
            'aria-label',
            'placeholder',
            'value',
            'alt',
            'aria-expanded',
            'aria_name'
        ]
    state = await ctx.deps.state
    elements_text = state.element_tree.clickable_elements_to_string(include_attributes=attr)
    if elements_text != '':
        extra = '... Cut off - use extract content or scroll to get more ...'
        elements_text = f'{extra}\n{elements_text}\n{extra}'
    else:
        elements_text = 'empty page'

    state_description = f"""
        Current title: {state.title}
        Current url: {state.url}
        Available tabs: {state.tabs}
        Interactive elements from current page view:
        {elements_text}
        """
    if state.screenshot:
        state_description += f'\nScreenshot: {{\n\t"type": "image_url",\n\t"image_url": {{"url": "data:image/png;base64,{state.screenshot}"}}\n}}'


    return state_description


@action.tool(retries=2)
async def search_google_tool(ctx: RunContext[AgentDeps], params: SearchGoogleAction):
    """Performs a Google search in the current browser tab."""
    browser_context = ctx.deps.browser_context
    return await search_google(params, browser_context)


@action.tool(retries=2)
async def go_to_url_tool(ctx: RunContext[AgentDeps], params: GoToUrlAction):
    """Navigates to a specified URL in the current browser tab."""
    browser_context = ctx.deps.browser_context
    return await go_to_url(params, browser_context)

@action.tool(retries=2)
async def click_element_tool(ctx: RunContext[AgentDeps], params: ClickElementAction):
    """Clicks an element identified by its index on the page."""
    browser_context = ctx.deps.browser_context
    return await click_element(params, browser_context)

@action.tool(retries=2)
async def input_text_tool(ctx: RunContext[AgentDeps], params: InputTextAction):
    """Inputs text into an interactive element on the page."""
    browser_context = ctx.deps.browser_context
    return await input_text(params, browser_context)

@action.tool(retries=2)
async def switch_tab_tool(ctx: RunContext[AgentDeps], params: SwitchTabAction):
    """Switches to a different browser tab by index."""
    browser_context = ctx.deps.browser_context
    return await switch_tab(params, browser_context)

@action.tool(retries=2)
async def open_tab_tool(ctx: RunContext[AgentDeps], params: OpenTabAction):
    """Opens a new browser tab with specified URL."""
    browser_context = ctx.deps.browser_context
    return await open_tab(params, browser_context)

@action.tool(retries=2)
async def extract_content_tool(ctx: RunContext[AgentDeps], params: ExtractPageContentAction):
    """Extracts page content in text or markdown format."""
    browser_context = ctx.deps.browser_context
    return await extract_content(params, browser_context)

@action.tool(retries=2)
async def scroll_down_tool(ctx: RunContext[AgentDeps], params: ScrollAction):
    """Scrolls the page down by specified amount or one page."""
    browser_context = ctx.deps.browser_context
    return await scroll_down(params, browser_context)

@action.tool(retries=2)
async def scroll_up_tool(ctx: RunContext[AgentDeps], params: ScrollAction):
    """Scrolls the page up by specified amount or one page."""
    browser_context = ctx.deps.browser_context
    return await scroll_up(params, browser_context)

@action.tool(retries=2)
async def send_keys_tool(ctx: RunContext[AgentDeps], params: SendKeysAction):
    """Sends keyboard input to the page."""
    browser_context = ctx.deps.browser_context
    return await send_keys(params, browser_context)

@action.tool(retries=2)
async def scroll_to_text_tool(ctx: RunContext[AgentDeps], text: str):
    """Scrolls page to first occurrence of specified text."""
    browser_context = ctx.deps.browser_context
    return await scroll_to_text(text, browser_context)

@action.tool(retries=2)
async def get_dropdown_options_tool(ctx: RunContext[AgentDeps], index: int):
    """Gets all available options from a dropdown element."""
    browser_context = ctx.deps.browser_context
    return await get_dropdown_options(index, browser_context)

@action.tool(retries=2)
async def select_dropdown_option_tool(ctx: RunContext[AgentDeps], index: int, text: str):
    """Selects an option in a dropdown by exact text match."""
    browser_context = ctx.deps.browser_context
    return await select_dropdown_option(index, text, browser_context)

@action.tool(retries=2)
async def go_back_tool(ctx: RunContext[AgentDeps]):
    """Navigates back to the previous page in browser history."""
    browser_context = ctx.deps.browser_context
    return await go_back(browser_context)

@action.tool(retries=2)
async def done_tool(ctx: RunContext[AgentDeps], params: DoneAction):
    """Signals completion of the current task with optional completion message."""
    return await done(params)
