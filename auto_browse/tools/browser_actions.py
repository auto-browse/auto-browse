import asyncio
import json
import logging
from typing import Any
from main_content_extractor import MainContentExtractor
from browser_use.browser.browser import BrowserContext

from browser_use.browser.browser import BrowserContext
from browser_use.controller.views import (
    SearchGoogleAction,
    GoToUrlAction,
    ClickElementAction,
    InputTextAction,
    DoneAction,
    SwitchTabAction,
    OpenTabAction,
    ExtractPageContentAction,
    ScrollAction,
    SendKeysAction
)
from browser_use.agent.views import ( ActionResult)


logger = logging.getLogger(__name__)

async def search_google(params: SearchGoogleAction, browser_context: BrowserContext):
    """Performs a Google search in the current browser tab.

    Args:
        params: SearchGoogleAction containing the search query
        browser_context: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing success message and search details

    Raises:
        Any exceptions from page navigation are propagated
    """
    page = await browser_context.get_current_page()
    await page.goto(f'https://www.google.com/search?q={params.query}&udm=14')
    await page.wait_for_load_state()
    msg = f'🔍  Searched for "{params.query}" in Google'
    logger.info(msg)
    return ActionResult(extracted_content=msg, include_in_memory=True)


async def go_to_url(params: GoToUrlAction, browser_context: BrowserContext):
    """Navigates to a specified URL in the current browser tab.

    Args:
        params: GoToUrlAction containing the target URL
        browser_context: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing navigation success message

    Raises:
        Any exceptions from page navigation are propagated
    """
    page = await browser_context.get_current_page()
    await page.goto(params.url)
    await page.wait_for_load_state()
    msg = f'🔗  Navigated to {params.url}'
    logger.info(msg)
    return ActionResult(extracted_content=msg, include_in_memory=True)


async def go_back(browser: BrowserContext):
	page = await browser.get_current_page()
	await page.go_back()
	await page.wait_for_load_state()
	msg = '🔙  Navigated back'
	logger.info(msg)
	return ActionResult(extracted_content=msg, include_in_memory=True)

#@self.registry.action('Click element', param_model=ClickElementAction, requires_browser=True)
async def click_element(params: ClickElementAction, browser: BrowserContext):
    """Clicks an element identified by its index on the page.

    Args:
        params: ClickElementAction containing the element index
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing click success message or error details

    Raises:
        Exception: If element index doesn't exist in selector map
    """
    session = await browser.get_session()
    state = session.cached_state

    if params.index not in state.selector_map:
        raise Exception(f'Element with index {params.index} does not exist - retry or use alternative actions')

    element_node = state.selector_map[params.index]
    initial_pages = len(session.context.pages)

    # if element has file uploader then dont click
    if await browser.is_file_uploader(element_node):
        msg = f'Index {params.index} - has an element which opens file upload dialog. To upload files please use a specific function to upload files '
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)

    msg = None

    try:
        await browser._click_element_node(element_node)
        msg = f'🖱️  Clicked button with index {params.index}: {element_node.get_all_text_till_next_clickable_element(max_depth=2)}'

        logger.info(msg)
        logger.debug(f'Element xpath: {element_node.xpath}')
        if len(session.context.pages) > initial_pages:
            new_tab_msg = 'New tab opened - switching to it'
            msg += f' - {new_tab_msg}'
            logger.info(new_tab_msg)
            await browser.switch_to_tab(-1)
        return ActionResult(extracted_content=msg, include_in_memory=True)
    except Exception as e:
        logger.warning(f'Element no longer available with index {params.index} - most likely the page changed')
        return ActionResult(error=str(e))

async def input_text(params: InputTextAction, browser: BrowserContext):
    """Inputs text into an interactive element on the page.

    Args:
        params: InputTextAction containing element index and text
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing input success message

    Raises:
        Exception: If element index doesn't exist in selector map
    """
    session = await browser.get_session()
    state = session.cached_state

    if params.index not in state.selector_map:
        raise Exception(f'Element index {params.index} does not exist - retry or use alternative actions')

    element_node = state.selector_map[params.index]
    await browser._input_text_element_node(element_node, params.text)
    msg = f'⌨️  Input "{params.text}" into index {params.index}'
    logger.info(msg)
    logger.debug(f'Element xpath: {element_node.xpath}')
    return ActionResult(extracted_content=msg, include_in_memory=True)

async def switch_tab(params: SwitchTabAction, browser: BrowserContext):
    """Switches to a different browser tab by index.

    Args:
        params: SwitchTabAction containing target page ID
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing tab switch success message
    """
    await browser.switch_to_tab(params.page_id)
    # Wait for tab to be ready
    page = await browser.get_current_page()
    await page.wait_for_load_state()
    msg = f'🔄  Switched to tab {params.page_id}'
    logger.info(msg)
    return ActionResult(extracted_content=msg, include_in_memory=True)

async def open_tab(params: OpenTabAction, browser: BrowserContext):
    """Opens a new browser tab with specified URL.

    Args:
        params: OpenTabAction containing target URL
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing new tab success message
    """
    await browser.create_new_tab(params.url)
    msg = f'🔗  Opened new tab with {params.url}'
    logger.info(msg)
    return ActionResult(extracted_content=msg, include_in_memory=True)

async def extract_content(params: ExtractPageContentAction, browser: BrowserContext):
    """Extracts page content in text or markdown format.

    Args:
        params: ExtractPageContentAction specifying content format
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing extracted page content
    """
    page = await browser.get_current_page()
    output_format = 'markdown' if params.include_links else 'text'
    content = MainContentExtractor.extract(  # type: ignore
        html=await page.content(),
        output_format=output_format,
    )
    msg = f'📄  Extracted page as {output_format}\n: {content}\n'
    logger.info(msg)
    return ActionResult(extracted_content=msg)

async def done(params: DoneAction):
    return ActionResult(is_done=True, extracted_content=params.text)

async def scroll_down(params: ScrollAction, browser: BrowserContext):
    """Scrolls the page down by specified amount or one page.

    Args:
        params: ScrollAction containing scroll amount (optional)
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing scroll success message
    """
    page = await browser.get_current_page()
    if params.amount is not None:
        await page.evaluate(f'window.scrollBy(0, {params.amount});')
    else:
        await page.keyboard.press('PageDown')

    amount = f'{params.amount} pixels' if params.amount is not None else 'one page'
    msg = f'🔍  Scrolled down the page by {amount}'
    logger.info(msg)
    return ActionResult(
        extracted_content=msg,
        include_in_memory=True,
    )

async def scroll_up(params: ScrollAction, browser: BrowserContext):
    """Scrolls the page up by specified amount or one page.

    Args:
        params: ScrollAction containing scroll amount (optional)
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing scroll success message
    """
    page = await browser.get_current_page()
    if params.amount is not None:
        await page.evaluate(f'window.scrollBy(0, -{params.amount});')
    else:
        await page.keyboard.press('PageUp')

    amount = f'{params.amount} pixels' if params.amount is not None else 'one page'
    msg = f'🔍  Scrolled up the page by {amount}'
    logger.info(msg)
    return ActionResult(
        extracted_content=msg,
        include_in_memory=True,
    )

async def send_keys(params: SendKeysAction, browser: BrowserContext):
    """Sends keyboard input to the page.

    Args:
        params: SendKeysAction containing keys to send
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing key press success message
    """
    page = await browser.get_current_page()

    await page.keyboard.press(params.keys)
    msg = f'⌨️  Sent keys: {params.keys}'
    logger.info(msg)
    return ActionResult(extracted_content=msg, include_in_memory=True)

async def scroll_to_text(text: str, browser: BrowserContext):  # type: ignore
    """Scrolls page to first occurrence of specified text.

    Args:
        text: Target text to scroll to
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing scroll success/failure message
    """
    page = await browser.get_current_page()
    try:
        # Try different locator strategies
        locators = [
            page.get_by_text(text, exact=False),
            page.locator(f'text={text}'),
            page.locator(f"//*[contains(text(), '{text}')]"),
        ]

        for locator in locators:
            try:
                # First check if element exists and is visible
                if await locator.count() > 0 and await locator.first.is_visible():
                    await locator.first.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)  # Wait for scroll to complete
                    msg = f'🔍  Scrolled to text: {text}'
                    logger.info(msg)
                    return ActionResult(extracted_content=msg, include_in_memory=True)
            except Exception as e:
                logger.debug(f'Locator attempt failed: {str(e)}')
                continue

        msg = f"Text '{text}' not found or not visible on page"
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)

    except Exception as e:
        msg = f"Failed to scroll to text '{text}': {str(e)}"
        logger.error(msg)
        return ActionResult(error=msg, include_in_memory=True)

async def get_dropdown_options(index: int, browser: BrowserContext) -> ActionResult:
    """Gets all available options from a dropdown element.

    Args:
        index: Element index of the dropdown
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing list of dropdown options or error message

    Raises:
        Exception: If element is not found or not a dropdown
    """
    page = await browser.get_current_page()
    selector_map = await browser.get_selector_map()
    dom_element = selector_map[index]

    try:
        # Frame-aware approach since we know it works
        all_options = []
        frame_index = 0

        for frame in page.frames:
            try:
                options = await frame.evaluate(
                    """
                    (xpath) => {
                        const select = document.evaluate(xpath, document, null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                        if (!select) return null;

                        return {
                            options: Array.from(select.options).map(opt => ({
                                text: opt.text, //do not trim, because we are doing exact match in select_dropdown_option
                                value: opt.value,
                                index: opt.index
                            })),
                            id: select.id,
                            name: select.name
                        };
                    }
                """,
                    dom_element.xpath,
                )

                if options:
                    logger.debug(f'Found dropdown in frame {frame_index}')
                    logger.debug(f'Dropdown ID: {options["id"]}, Name: {options["name"]}')

                    formatted_options = []
                    for opt in options['options']:
                        # encoding ensures AI uses the exact string in select_dropdown_option
                        encoded_text = json.dumps(opt['text'])
                        formatted_options.append(f'{opt["index"]}: text={encoded_text}')

                    all_options.extend(formatted_options)

            except Exception as frame_e:
                logger.debug(f'Frame {frame_index} evaluation failed: {str(frame_e)}')

            frame_index += 1

        if all_options:
            msg = '\n'.join(all_options)
            msg += '\nUse the exact text string in select_dropdown_option'
            logger.info(msg)
            return ActionResult(extracted_content=msg, include_in_memory=True)
        else:
            msg = 'No options found in any frame for dropdown'
            logger.info(msg)
            return ActionResult(extracted_content=msg, include_in_memory=True)

    except Exception as e:
        logger.error(f'Failed to get dropdown options: {str(e)}')
        msg = f'Error getting options: {str(e)}'
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)

async def select_dropdown_option(
    index: int,
    text: str,
    browser: BrowserContext,
) -> ActionResult:
    """Selects an option in a dropdown by exact text match.

    Args:
        index: Element index of the dropdown
        text: Exact text of option to select
        browser: BrowserContext instance for browser interaction

    Returns:
        ActionResult containing selection success/failure message

    Raises:
        Exception: If element is not a select element
    """
    page = await browser.get_current_page()
    selector_map = await browser.get_selector_map()
    dom_element = selector_map[index]

    # Validate that we're working with a select element
    if (dom_element.tag_name != 'select'):
        logger.error(f'Element is not a select! Tag: {dom_element.tag_name}, Attributes: {dom_element.attributes}')
        msg = f'Cannot select option: Element with index {index} is a {dom_element.tag_name}, not a select'
        return ActionResult(extracted_content=msg, include_in_memory=True)

    logger.debug(f"Attempting to select '{text}' using xpath: {dom_element.xpath}")
    logger.debug(f'Element attributes: {dom_element.attributes}')
    logger.debug(f'Element tag: {dom_element.tag_name}')

    xpath = '//' + dom_element.xpath

    try:
        frame_index = 0
        for frame in page.frames:
            try:
                logger.debug(f'Trying frame {frame_index} URL: {frame.url}')

                # First verify we can find the dropdown in this frame
                find_dropdown_js = """
                    (xpath) => {
                        try {
                            const select = document.evaluate(xpath, document, null,
                                XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (!select) return null;
                            if (select.tagName.toLowerCase() !== 'select') {
                                return {
                                    error: `Found element but it's a ${select.tagName}, not a SELECT`,
                                    found: false
                                };
                            }
                            return {
                                id: select.id,
                                name: select.name,
                                found: true,
                                tagName: select.tagName,
                                optionCount: select.options.length,
                                currentValue: select.value,
                                availableOptions: Array.from(select.options).map(o => o.text.trim())
                            };
                        } catch (e) {
                            return {error: e.toString(), found: false};
                        }
                    }
                """

                dropdown_info = await frame.evaluate(find_dropdown_js, dom_element.xpath)

                if dropdown_info:
                    if not dropdown_info.get('found'):
                        logger.error(f'Frame {frame_index} error: {dropdown_info.get("error")}')
                        continue

                    logger.debug(f'Found dropdown in frame {frame_index}: {dropdown_info}')

                    # "label" because we are selecting by text
                    # nth(0) to disable error thrown by strict mode
                    # timeout=1000 because we are already waiting for all network events, therefore ideally we don't need to wait a lot here (default 30s)
                    selected_option_values = (
                        await frame.locator('//' + dom_element.xpath).nth(0).select_option(label=text, timeout=1000)
                    )

                    msg = f'selected option {text} with value {selected_option_values}'
                    logger.info(msg + f' in frame {frame_index}')

                    return ActionResult(extracted_content=msg, include_in_memory=True)

            except Exception as frame_e:
                logger.error(f'Frame {frame_index} attempt failed: {str(frame_e)}')
                logger.error(f'Frame type: {type(frame)}')
                logger.error(f'Frame URL: {frame.url}')

            frame_index += 1

        msg = f"Could not select option '{text}' in any frame"
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)

    except Exception as e:
        msg = f'Selection failed: {str(e)}'
        logger.error(msg)
        return ActionResult(error=msg, include_in_memory=True)
