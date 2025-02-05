"""Browser DOM capture service"""
import logging
from importlib import resources

from playwright.async_api import Page

from browser_capture.views import DOMState, DOMElementNode, DOMTextNode, DOMBaseNode, SelectorMap

logger = logging.getLogger(__name__)

class DomService:
    """Service for handling DOM interactions"""

    def __init__(self, page: Page):
        self.page = page
        self.xpath_cache = {}

    async def get_clickable_elements(
        self,
        highlight_elements: bool = True,
        focus_element: int = -1,
        viewport_expansion: int = 0,
    ) -> DOMState:
        """Get clickable elements from the page"""
        element_tree = await self._build_dom_tree(
            highlight_elements, focus_element, viewport_expansion
        )
        selector_map = self._create_selector_map(element_tree)

        return DOMState(element_tree=element_tree, selector_map=selector_map)

    async def _build_dom_tree(
        self,
        highlight_elements: bool,
        focus_element: int,
        viewport_expansion: int,
    ) -> DOMElementNode:
        """Build DOM tree from page content"""
        # Define JavaScript functions for DOM tree building
        js_functions = """
        window.domCapture = {
            highlightIndex: 0,

            getXPath(node) {
                if (!node || !node.nodeName) return "";
                let name = node.nodeName.toLowerCase();
                const parent = node.parentNode;
                if (!parent) return name;

                const siblings = parent.children;
                let siblingCount = 0;
                let siblingIndex = 0;

                for (let i = 0; i < siblings.length; i++) {
                    if (siblings[i].nodeName.toLowerCase() === name) {
                        if (siblings[i] === node) {
                            siblingIndex = siblingCount;
                        }
                        siblingCount++;
                    }
                }

                if (siblingCount > 1) {
                    name += `[${siblingIndex + 1}]`;
                }

                const parentPath = this.getXPath(parent);
                return parentPath ? parentPath + "/" + name : name;
            },

            isElementVisible(element) {
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return (
                    style.display !== "none" &&
                    style.visibility !== "hidden" &&
                    style.opacity !== "0" &&
                    rect.width > 0 &&
                    rect.height > 0
                );
            },

            isInteractive(element) {
                const interactiveTags = ["a", "button", "input", "select", "textarea", "summary"];
                const interactiveRoles = ["button", "link", "checkbox", "radio", "tab", "menuitem", "option"];

                return (
                    interactiveTags.includes(element.tagName.toLowerCase()) ||
                    (element.hasAttribute("role") && interactiveRoles.includes(element.getAttribute("role").toLowerCase())) ||
                    element.hasAttribute("tabindex") ||
                    element.hasAttribute("contenteditable") ||
                    element.hasAttribute("onclick") ||
                    (element.tagName.toLowerCase() === "div" && element.hasAttribute("role"))
                );
            },

            buildDomTree(node, highlightElements, focusHighlightIndex, viewportExpansion) {
                if (!node) return null;

                if (node.nodeName.toLowerCase() === "script" || node.nodeName.toLowerCase() === "style") {
                    return null;
                }

                if (node.nodeType === 3) {
                    const text = node.textContent.trim();
                    if (!text) return null;
                    return {
                        type: "TEXT_NODE",
                        text: text,
                        isVisible: this.isElementVisible(node.parentElement)
                    };
                }

                if (node.nodeType !== 1) return null;

                const isVisible = this.isElementVisible(node);
                const rect = node.getBoundingClientRect();
                const viewport = {
                    top: -viewportExpansion,
                    bottom: window.innerHeight + viewportExpansion,
                    left: 0,
                    right: window.innerWidth
                };

                if (!isVisible && !this.isInteractive(node)) return null;
                if (rect.bottom < viewport.top || rect.top > viewport.bottom) return null;

                const nodeData = {
                    tagName: node.nodeName.toLowerCase(),
                    xpath: this.getXPath(node),
                    attributes: {},
                    isVisible: isVisible,
                    isInteractive: this.isInteractive(node),
                    children: []
                };

                for (let i = 0; i < node.attributes.length; i++) {
                    const attr = node.attributes[i];
                    nodeData.attributes[attr.name] = attr.value;
                }

                if (node.shadowRoot) {
                    nodeData.shadowRoot = true;
                }

                for (const child of node.childNodes) {
                    const childData = this.buildDomTree(child, highlightElements, focusHighlightIndex, viewportExpansion);
                    if (childData) nodeData.children.push(childData);
                }

                if (highlightElements && this.isInteractive(node)) {
                    nodeData.highlightIndex = this.highlightIndex++;
                    if (nodeData.highlightIndex === focusHighlightIndex) {
                        nodeData.isTopElement = true;
                    }

                    node.setAttribute(
                        "browser-user-highlight-id",
                        `playwright-highlight-${nodeData.highlightIndex}`
                    );
                }

                return nodeData;
            },

            captureState(options) {
                // Clear any existing highlights
                const existingContainer = document.getElementById("playwright-highlight-container");
                if (existingContainer) {
                    existingContainer.remove();
                }

                // Reset highlight index
                this.highlightIndex = 0;

                return this.buildDomTree(
                    document.documentElement,
                    options.highlightElements,
                    options.focusElement,
                    options.viewportExpansion
                );
            }
        };
        """

        # Evaluate the JavaScript functions
        await self.page.evaluate(js_functions)

        # Call the captureState function with options
        eval_page = await self.page.evaluate("""(options) => {
            return window.domCapture.captureState(options);
        }""", {
            "highlightElements": highlight_elements,
            "focusElement": focus_element,
            "viewportExpansion": viewport_expansion
        })

        html_to_dict = self._parse_node(eval_page)

        if not isinstance(html_to_dict, DOMElementNode):
            raise ValueError('Failed to parse HTML to dictionary')

        return html_to_dict

    def _create_selector_map(self, element_tree: DOMElementNode) -> SelectorMap:
        """Create a map of selectors from the element tree"""
        selector_map = {}

        def process_node(node: DOMBaseNode):
            if isinstance(node, DOMElementNode) and node.highlight_index is not None:
                selector_map[node.highlight_index] = node

            if isinstance(node, DOMElementNode):
                for child in node.children:
                    process_node(child)

        process_node(element_tree)
        return selector_map

    def _parse_node(
        self,
        node_data: dict,
        parent: DOMElementNode | None = None,
    ) -> DOMElementNode | DOMTextNode | None:
        """Parse a node from the DOM data"""
        if not node_data:
            return None

        if node_data.get('type') == 'TEXT_NODE':
            text_node = DOMTextNode(
                text=node_data['text'],
                is_visible=node_data['isVisible'],
                parent=parent,
            )
            return text_node

        tag_name = node_data['tagName']

        element_node = DOMElementNode(
            tag_name=tag_name,
            xpath=node_data['xpath'],
            attributes=node_data.get('attributes', {}),
            children=[],  # Initialize empty, will fill later
            is_visible=node_data.get('isVisible', False),
            is_interactive=node_data.get('isInteractive', False),
            is_top_element=node_data.get('isTopElement', False),
            highlight_index=node_data.get('highlightIndex'),
            shadow_root=node_data.get('shadowRoot', False),
            parent=parent,
        )

        children = []
        for child in node_data.get('children', []):
            if child is not None:
                child_node = self._parse_node(child, parent=element_node)
                if child_node is not None:
                    children.append(child_node)

        element_node.children = children

        return element_node
