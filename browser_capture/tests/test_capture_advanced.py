import pytest
import pytest_asyncio
from playwright.async_api import async_playwright
from browser_capture.service import DomService
from browser_capture.views import DOMElementNode, DOMBaseNode

@pytest_asyncio.fixture
async def page():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        yield page
        await context.close()
        await browser.close()

@pytest.mark.asyncio
async def test_shadow_dom_handling(page):
    """Test capturing elements inside shadow DOM"""
    await page.set_content("""
        <div id="host"></div>
    """)

    # Verify host element exists (state:'attached' doesn't check visibility)
    await page.wait_for_selector('#host', state='attached')

    # Make the host element visible
    await page.evaluate("""() => {
        const host = document.getElementById('host');
        host.style.display = 'block';
        host.style.width = '100px';
        host.style.height = '100px';
    }""")

    # Setup and verify shadow DOM
    shadow_check = await page.evaluate("""() => {
        const host = document.getElementById('host');
        if (!host) {
            console.error('Host element not found');
            return false;
        }

        // Create and attach shadow root
        const shadow = host.attachShadow({mode: 'open'});

        // Create shadow DOM content
        const div = document.createElement('div');
        const button = document.createElement('button');
        button.textContent = 'Shadow Button';
        const input = document.createElement('input');
        input.type = 'text';

        // Add elements to shadow DOM
        div.appendChild(button);
        div.appendChild(input);
        shadow.appendChild(div);

        // Verify shadow root was created
        const verifyHost = document.getElementById('host');
        console.log('Shadow root check:', {
            hostFound: !!verifyHost,
            hasShadowRoot: !!verifyHost?.shadowRoot,
            shadowMode: verifyHost?.shadowRoot?.mode,
            childrenCount: verifyHost?.shadowRoot?.children?.length
        });

        return !!verifyHost?.shadowRoot;
    }""")

    assert shadow_check, "Shadow root was not properly created"

    # Wait for shadow DOM content to process
    await page.wait_for_timeout(100)

    service = DomService(page)
    dom_state = await service.get_clickable_elements()

    # Debug DOM state
    def print_tree(node: DOMBaseNode, level: int = 0):
        indent = "  " * level
        if isinstance(node, DOMElementNode):
            print(f"{indent}Node: {node.tag_name}, id={node.attributes.get('id')}, shadow_root={node.shadow_root}")
            for child in node.children:
                print_tree(child, level + 1)

    print("\nDOM Tree Structure:")
    print_tree(dom_state.element_tree)
    print("\nSelector Map Contents:")
    for idx, node in dom_state.selector_map.items():
        print(f"Index {idx}: {node.tag_name}, id={node.attributes.get('id')}, shadow_root={node.shadow_root}")

    # First check full tree for shadow hosts
    def find_shadow_hosts(node: DOMBaseNode) -> list[DOMElementNode]:
        hosts = []
        if isinstance(node, DOMElementNode):
            if node.shadow_root:
                hosts.append(node)
            for child in node.children:
                hosts.extend(find_shadow_hosts(child))
        return hosts

    shadow_hosts = find_shadow_hosts(dom_state.element_tree)
    assert len(shadow_hosts) == 1, "Expected exactly one shadow host in the element tree"

    # Verify shadow content was captured
    shadow_elements = [
        node for node in dom_state.selector_map.values()
        if node.tag_name in ('button', 'input')
    ]
    assert len(shadow_elements) == 2

@pytest.mark.asyncio
async def test_viewport_expansion(page):
    """Test capturing elements with viewport expansion"""
    # Create a tall page with buttons at different scroll positions
    await page.set_content("""
        <style>
            .spacer { height: 2000px; }
            button { position: absolute; }
            #top { top: 0; }
            #middle { top: 1000px; }
            #bottom { top: 2000px; }
        </style>
        <div class="spacer">
            <button id="top">Top Button</button>
            <button id="middle">Middle Button</button>
            <button id="bottom">Bottom Button</button>
        </div>
    """)

    service = DomService(page)

    # Test without viewport expansion
    dom_state = await service.get_clickable_elements(viewport_expansion=0)
    visible_buttons = [
        node for node in dom_state.selector_map.values()
        if node.tag_name == 'button' and node.is_visible
    ]
    initial_count = len(visible_buttons)

    # Test with viewport expansion
    dom_state = await service.get_clickable_elements(viewport_expansion=2000)
    expanded_buttons = [
        node for node in dom_state.selector_map.values()
        if node.tag_name == 'button' and node.is_visible
    ]
    assert len(expanded_buttons) > initial_count

@pytest.mark.asyncio
async def test_nested_iframes(page):
    """Test capturing elements inside nested iframes"""
    await page.set_content("""
        <iframe id="frame1"></iframe>
        <button>Main Button</button>
    """)

    # Wait for first frame
    frame1 = await page.wait_for_selector('#frame1')

    # Set content for first frame
    await page.evaluate("""() => {
        const frame1 = document.getElementById('frame1');
        frame1.srcdoc = `
            <iframe id="frame2"></iframe>
            <button>Frame 1 Button</button>
        `;
    }""")

    # Wait for second frame to load
    await page.wait_for_timeout(100)  # Wait for frame1 content to load

    # Set content for second frame
    await page.evaluate("""() => {
        const frame1 = document.getElementById('frame1');
        const frame2 = frame1.contentDocument.getElementById('frame2');
        frame2.srcdoc = `
            <button>Deep Button</button>
            <input type="text">
        `;
    }""")

    await page.wait_for_timeout(100)  # Wait for frame2 content to load

    service = DomService(page)
    dom_state = await service.get_clickable_elements()

    # Should capture buttons from all frames
    buttons = [
        node for node in dom_state.selector_map.values()
        if node.tag_name == 'button'
    ]
    assert len(buttons) == 3

@pytest.mark.asyncio
async def test_dynamic_content(page):
    """Test capturing dynamically added elements"""
    await page.set_content("""
        <div id="container">
            <button>Initial Button</button>
        </div>
        <script>
            setTimeout(() => {
                const btn = document.createElement('button');
                btn.textContent = 'Dynamic Button';
                document.getElementById('container').appendChild(btn);
            }, 100);
        </script>
    """)

    # Wait for dynamic content
    await page.wait_for_timeout(200)

    service = DomService(page)
    dom_state = await service.get_clickable_elements()

    # Should capture both initial and dynamic buttons
    buttons = [
        node for node in dom_state.selector_map.values()
        if node.tag_name == 'button'
    ]
    assert len(buttons) == 2

@pytest.mark.asyncio
async def test_xpath_generation(page):
    """Test accurate xpath generation for elements"""
    await page.set_content("""
        <div>
            <button>First</button>
            <div>
                <button>Second</button>
                <button>Third</button>
            </div>
            <button>Fourth</button>
        </div>
    """)

    service = DomService(page)
    dom_state = await service.get_clickable_elements()

    # Get buttons and verify their text and uniqueness
    buttons = sorted([
        node for node in dom_state.selector_map.values()
        if node.tag_name == 'button'
    ], key=lambda x: x.xpath)
    assert len(buttons) == 4

    # Verify each button's text content
    button_texts = [button.get_all_text_till_next_clickable_element().strip() for button in buttons]
    assert 'First' in button_texts
    assert 'Second' in button_texts
    assert 'Third' in button_texts
    assert 'Fourth' in button_texts

    # Verify each button has a unique xpath
    xpaths = set(button.xpath for button in buttons)
    assert len(xpaths) == len(buttons)

    # Verify we can find each button using a text selector
    for button in buttons:
        text = button.get_all_text_till_next_clickable_element().strip()
        element = await page.query_selector(f'button:has-text("{text}")')
        assert element is not None
