import pytest
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from browser_state.manager import StateManager
from browser_state.models import BrowserState, ViewportState

@pytest.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        yield browser
        await browser.close()

@pytest.fixture
async def context(browser: Browser):
    context = await browser.new_context()
    yield context
    await context.close()

@pytest.fixture
async def page(context: BrowserContext):
    page = await context.new_page()
    yield page
    await page.close()

@pytest.mark.asyncio
async def test_viewport_state_capture(page: Page):
    """Test viewport state capture"""
    state_manager = StateManager(page)

    # Create a page with known dimensions
    html_content = """
        <html><body style='height: 2000px; margin: 0; padding: 0;'>
            <div style='height: 2000px;'>Long page</div>
        </body></html>
    """
    await page.set_content(html_content)
    await page.set_viewport_size({"width": 1280, "height": 800})

    # Get initial viewport state
    viewport = await state_manager.get_viewport_state()
    assert isinstance(viewport, ViewportState)
    assert viewport.pixels_above == 0  # Should be at top
    assert viewport.pixels_below > 1000  # Should have scrollable content
    assert viewport.width == 1280
    assert viewport.height == 800

    # Scroll down and check updated state
    await page.evaluate("window.scrollTo(0, 500)")
    viewport = await state_manager.get_viewport_state()
    assert viewport.pixels_above == 500
    assert viewport.pixels_below > 500

@pytest.mark.asyncio
async def test_complete_state_capture(page: Page):
    """Test complete browser state capture"""
    state_manager = StateManager(page)

    # Create a test page with interactive elements
    html_content = """
        <html><body>
            <h1>Test Page</h1>
            <button id="test-button">Click Me</button>
            <div style="margin-top: 2000px;">Bottom content</div>
        </body></html>
    """
    await page.set_content(html_content)
    await page.set_viewport_size({"width": 1280, "height": 800})

    # Capture state with screenshot
    state = await state_manager.capture_state(include_screenshot=True)

    # Verify state components
    assert isinstance(state, BrowserState)
    assert "Test Page" in await page.content()
    assert state.dom_tree is not None
    assert len(state.selector_map) > 0  # Should have at least one interactive element
    assert state.viewport.height == 800
    assert state.viewport.width == 1280
    assert state.screenshot is not None
    assert len(state.tabs) > 0

@pytest.mark.asyncio
async def test_tabs_info(context: BrowserContext):
    """Test tabs information capture"""
    # Create multiple pages in the context
    page1 = await context.new_page()
    await page1.set_content("<html><body>Tab 1</body></html>")

    page2 = await context.new_page()
    await page2.set_content("<html><body>Tab 2</body></html>")

    state_manager = StateManager(page1)
    tabs = await state_manager.get_tabs_info()

    assert len(tabs) == 2
    assert "Tab 1" in await page1.content()
    assert "Tab 2" in await page2.content()

@pytest.mark.asyncio
async def test_screenshot_capture(page: Page):
    """Test screenshot capture"""
    state_manager = StateManager(page)
    await page.set_content("<html><body><h1>Screenshot Test</h1></body></html>")

    # Take screenshot
    screenshot = await state_manager.take_screenshot()

    assert screenshot is not None
    assert isinstance(screenshot, str)
    assert len(screenshot) > 0  # Should have base64 content
