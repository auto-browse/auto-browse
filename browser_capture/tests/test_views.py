import pytest
from playwright.sync_api import sync_playwright
from browser_capture.views import DOMElementNode, DOMTextNode, DOMState

@pytest.fixture
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        yield page
        browser.close()

def test_dom_tree_creation():
    # Create a simple DOM tree
    root = DOMElementNode(
        tag_name="div",
        xpath="/div",
        attributes={},
        children=[],
        is_visible=True,
        parent=None
    )

    text_node = DOMTextNode(
        text="Hello World",
        is_visible=True,
        parent=root
    )

    root.children.append(text_node)

    assert root.tag_name == "div"
    assert len(root.children) == 1
    assert isinstance(root.children[0], DOMTextNode)
    assert root.children[0].text == "Hello World"

def test_screenshot_capture(browser):
    # Navigate to a test page and capture screenshot
    browser.goto("data:text/html,<html><body><h1>Test Page</h1></body></html>")
    screenshot_bytes = browser.screenshot()
    assert len(screenshot_bytes) > 0

def test_clickable_elements():
    # Create a DOM tree with clickable elements
    root = DOMElementNode(
        tag_name="div",
        xpath="/div",
        attributes={},
        children=[],
        is_visible=True,
        parent=None
    )

    button = DOMElementNode(
        tag_name="button",
        xpath="/div/button",
        attributes={"class": "test-button"},
        children=[],
        is_visible=True,
        parent=root,
        is_interactive=True,
        highlight_index=1
    )

    button_text = DOMTextNode(
        text="Click Me",
        is_visible=True,
        parent=button
    )

    button.children.append(button_text)
    root.children.append(button)

    # Test clickable elements string representation
    clickable_str = root.clickable_elements_to_string()
    assert "1[:]<button" in clickable_str
    assert "Click Me" in clickable_str

def test_file_upload_element():
    # Create a DOM tree with file upload input
    root = DOMElementNode(
        tag_name="form",
        xpath="/form",
        attributes={},
        children=[],
        is_visible=True,
        parent=None
    )

    file_input = DOMElementNode(
        tag_name="input",
        xpath="/form/input",
        attributes={"type": "file"},
        children=[],
        is_visible=True,
        parent=root
    )

    root.children.append(file_input)

    # Test file upload element detection
    found_input = root.get_file_upload_element()
    assert found_input is not None
    assert found_input.tag_name == "input"
    assert found_input.attributes["type"] == "file"

def test_interactive_page_elements(browser):
    # Create a test page with interactive elements
    html_content = """
        <html>
            <body>
                <button id="test-button">Click Me</button>
                <input type="text" id="test-input">
                <input type="file" id="file-input">
            </body>
        </html>
    """
    browser.goto(f"data:text/html,{html_content}")

    # Test button presence
    button = browser.locator("#test-button")
    assert button.is_visible()

    # Test text input
    text_input = browser.locator("#test-input")
    assert text_input.is_visible()

    # Test file input
    file_input = browser.locator("#file-input")
    assert file_input.is_visible()
