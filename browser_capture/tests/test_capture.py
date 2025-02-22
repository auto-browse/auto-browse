import pytest
import pytest_asyncio
from playwright.async_api import async_playwright
from browser_capture.service import DomService
from browser_capture.views import DOMElementNode, DOMTextNode

@pytest_asyncio.fixture
async def page():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        yield page
        await context.close()
        await browser.close()

def verify_dom_node(node):
    """Helper to verify DOMNode properties"""
    assert isinstance(node, (DOMElementNode, DOMTextNode))
    if isinstance(node, DOMElementNode):
        assert hasattr(node, 'tag_name')
        assert hasattr(node, 'xpath')
        assert hasattr(node, 'is_visible')
        assert hasattr(node, 'is_interactive')
        assert hasattr(node, 'children')
    elif isinstance(node, DOMTextNode):
        assert hasattr(node, 'text')
        assert hasattr(node, 'is_visible')

@pytest.mark.asyncio
async def test_basic_dom_capture(page):
    """Test capturing basic DOM structure"""
    await page.set_content("""
        <div>
            <button>Click me</button>
            <input type="text" value="test">
            <p>Some text</p>
        </div>
    """)

    service = DomService(page)
    dom_state = await service.get_clickable_elements()

    # Verify basic structure
    assert dom_state.element_tree is not None
    verify_dom_node(dom_state.element_tree)

    # Verify selector map has interactive elements
    assert len(dom_state.selector_map) > 0
    # Should have button and input
    assert len([node for node in dom_state.selector_map.values()
               if node.tag_name in ('button', 'input')]) == 2

@pytest.mark.asyncio
async def test_highlight_elements(page):
    """Test element highlighting functionality"""
    await page.set_content("""
        <div>
            <button id="btn1">Button 1</button>
            <button id="btn2">Button 2</button>
        </div>
    """)

    service = DomService(page)
    dom_state = await service.get_clickable_elements(highlight_elements=True)

    # Verify highlights were added
    for node in dom_state.selector_map.values():
        if node.tag_name == 'button':
            assert node.highlight_index is not None
            # Verify highlight attribute was added to element
            element = await page.query_selector(
                f'[browser-user-highlight-id="playwright-highlight-{node.highlight_index}"]'
            )
            assert element is not None

@pytest.mark.asyncio
async def test_interactive_element_detection(page):
    """Test detection of various interactive elements"""
    await page.set_content("""
        <div>
            <button>Standard Button</button>
            <div role="button">ARIA Button</div>
            <a href="#">Link</a>
            <input type="text">
            <select><option>Option</option></select>
            <div onclick="alert('click')">Click Handler</div>
            <div tabindex="0">Focusable</div>
        </div>
    """)

    service = DomService(page)
    dom_state = await service.get_clickable_elements()

    interactive_tags = set()
    for node in dom_state.selector_map.values():
        if node.is_interactive:
            interactive_tags.add(node.tag_name)

    assert 'button' in interactive_tags
    assert 'div' in interactive_tags  # ARIA button and click handler
    assert 'a' in interactive_tags
    assert 'input' in interactive_tags
    assert 'select' in interactive_tags

@pytest.mark.asyncio
async def test_visibility_detection(page):
    """Test detection of visible and hidden elements"""
    await page.set_content("""
        <div>
            <button style="display: none">Hidden Button</button>
            <button style="visibility: hidden">Invisible Button</button>
            <button style="opacity: 0">Transparent Button</button>
            <button id="visible">Visible Button</button>
            <button style="position: absolute; left: -9999px">Off-screen Button</button>
        </div>
    """)

    service = DomService(page)
    dom_state = await service.get_clickable_elements()

    # Get only truly visible buttons (not hidden, not off-screen)
    visible_buttons = [
        node for node in dom_state.selector_map.values()
        if (node.tag_name == 'button' and
            node.is_visible and
            not node.attributes.get('style', '').startswith('position: absolute'))
    ]

    assert len(visible_buttons) == 1
    assert visible_buttons[0].attributes.get('id') == 'visible'

@pytest.mark.asyncio
async def test_focus_element(page):
    """Test focusing on specific element"""
    await page.set_content("""
        <div>
            <button id="btn1">Button 1</button>
            <button id="btn2">Button 2</button>
        </div>
    """)

    service = DomService(page)
    # Focus on the second button (index 1)
    dom_state = await service.get_clickable_elements(focus_element=1)

    # Verify the second button is marked as top element
    assert any(node.is_top_element and node.highlight_index == 1
              for node in dom_state.selector_map.values())
