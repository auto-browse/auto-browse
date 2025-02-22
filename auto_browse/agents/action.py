from dataclasses import dataclass
from datetime import datetime
import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.test import TestModel
from auto_browse.browser.views import (
    ActionResult,
    ClickElementAction,
    DoneAction,
    ExtractPageContentAction,
    GoToUrlAction,
    InputTextAction,
    OpenTabAction,
    ScrollAction,
    SearchGoogleAction,
    SendKeysAction,
    SwitchTabAction
)
#from browser_init.context import BrowserContext
#from browser_state.models import BrowserState

from auto_browse.dependencies.common_dependencies import AgentDeps
from auto_browse.tools.browser_actions import (
    search_google, go_to_url, click_element, input_text, switch_tab,
    open_tab, extract_content, scroll_down, scroll_up, send_keys,
    scroll_to_text, get_dropdown_options, select_dropdown_option, go_back, done
)



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
        5. Before you call the tool, make sure to check the results of the previous tool call. If the task is already completed, you can call the 'done' tool to signal completion.
        6. You can make max two tool calls in a single action. First tool call to take action and second tool call will be the done tool call. No more tool calls will be allowed after the done tool call.
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
    state =  ctx.deps.state
    elements_text = state.dom_tree.clickable_elements_to_string(include_attributes=attr)
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
    logger.info(f"Searching Google for: {params.query}")
    browser_context = ctx.deps.browser_context
    return await search_google(params, browser_context)


@action.tool(retries=2)
async def go_to_url_tool(ctx: RunContext[AgentDeps], params: GoToUrlAction):
    """Navigates to a specified URL in the current browser tab."""
    logger.info(f"Going to URL: {params.url}")
    browser_context = ctx.deps.browser_context
    return await go_to_url(params, browser_context)

@action.tool(retries=2)
async def click_element_tool(ctx: RunContext[AgentDeps], params: ClickElementAction):
    """Clicks an element identified by its index on the page."""
    logger.info(f"Clicking element at index: {params.index}")
    browser_context = ctx.deps.browser_context
    return await click_element(params, browser_context)

@action.tool(retries=2)
async def input_text_tool(ctx: RunContext[AgentDeps], params: InputTextAction):
    """Inputs text into an interactive element on the page."""
    logger.info(f"Inputting text: {params.text}")
    browser_context = ctx.deps.browser_context
    return await input_text(params, browser_context)

@action.tool(retries=2)
async def switch_tab_tool(ctx: RunContext[AgentDeps], params: SwitchTabAction):
    """Switches to a different browser tab by index."""
    logger.info(f"Switching to tab: {params.page_id}")
    browser_context = ctx.deps.browser_context
    return await switch_tab(params, browser_context)

@action.tool(retries=2)
async def open_tab_tool(ctx: RunContext[AgentDeps], params: OpenTabAction):
    """Opens a new browser tab with specified URL."""
    logger.info(f"Opening new tab with URL: {params.url}")
    browser_context = ctx.deps.browser_context
    return await open_tab(params, browser_context)

@action.tool(retries=2)
async def extract_content_tool(ctx: RunContext[AgentDeps], params: ExtractPageContentAction):
    """Extracts page content in text or markdown format."""
    logger.info(f"Extracting page content")
    browser_context = ctx.deps.browser_context
    return await extract_content(params, browser_context)

@action.tool(retries=2)
async def scroll_down_tool(ctx: RunContext[AgentDeps], params: ScrollAction):
    """Scrolls the page down by specified amount or one page."""
    logger.info(f"Scrolling down by: {params.amount}")
    browser_context = ctx.deps.browser_context
    return await scroll_down(params, browser_context)

@action.tool(retries=2)
async def scroll_up_tool(ctx: RunContext[AgentDeps], params: ScrollAction):
    """Scrolls the page up by specified amount or one page."""
    logger.info(f"Scrolling up by: {params.amount}")
    browser_context = ctx.deps.browser_context
    return await scroll_up(params, browser_context)

@action.tool(retries=2)
async def send_keys_tool(ctx: RunContext[AgentDeps], params: SendKeysAction):
    """Sends keyboard input to the page."""
    logger.info(f"Sending keys: {params.keys}")
    browser_context = ctx.deps.browser_context
    return await send_keys(params, browser_context)

@action.tool(retries=2)
async def scroll_to_text_tool(ctx: RunContext[AgentDeps], text: str):
    """Scrolls page to first occurrence of specified text."""
    logger.info(f"Scrolling to text: {text}")
    browser_context = ctx.deps.browser_context
    return await scroll_to_text(text, browser_context)

@action.tool(retries=2)
async def get_dropdown_options_tool(ctx: RunContext[AgentDeps], index: int):
    """Gets all available options from a dropdown element."""
    logger.info(f"Getting dropdown options")
    browser_context = ctx.deps.browser_context
    return await get_dropdown_options(index, browser_context)

@action.tool(retries=2)
async def select_dropdown_option_tool(ctx: RunContext[AgentDeps], index: int, text: str):
    """Selects an option in a dropdown by exact text match."""
    logger.info(f"Selecting dropdown option: {text}")
    browser_context = ctx.deps.browser_context
    return await select_dropdown_option(index, text, browser_context)

@action.tool(retries=2)
async def go_back_tool(ctx: RunContext[AgentDeps]):
    """Navigates back to the previous page in browser history."""
    logger.info(f"Going back")
    browser_context = ctx.deps.browser_context
    return await go_back(browser_context)

@action.tool(retries=2)
async def done_tool(ctx: RunContext[AgentDeps], params: DoneAction):
    """Signals completion of the current task with optional completion message."""
    logger.info(f"Task completed")
    return await done(params)
