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
                if (!element) return false;
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

            processShadowRoot(shadowRoot, options) {
                if (!shadowRoot) return [];

                const children = [];
                for (const child of shadowRoot.children) {
                    const childData = this.buildDomTree(child, options);
                    if (childData) children.push(childData);
                }
                return children;
            },

            processIframe(iframe, options) {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!iframeDoc) return null;

                    const children = [];
                    for (const child of iframeDoc.body.children) {
                        const childData = this.buildDomTree(child, options);
                        if (childData) children.push(childData);
                    }
                    return children;
                } catch (e) {
                    console.warn('Failed to access iframe content:', e);
                    return null;
                }
            },

            buildDomTree(node, options) {
                if (!node) return null;

                const { highlightElements, focusElement, viewportExpansion } = options;

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

                // Check if this is a shadow host
                const isShadowHost = !!node.shadowRoot;
                console.log('Node check:', {
                    nodeName: node.nodeName,
                    id: node.id,
                    isShadowHost,
                    isVisible,
                    isInteractive: this.isInteractive(node)
                });

                // Always include shadow hosts and interactive/visible elements
                if (!isShadowHost && !isVisible && !this.isInteractive(node)) {
                    console.log('Skipping node:', node.nodeName, node.id);
                    return null;
                }
                if (!isShadowHost && rect.bottom < viewport.top || rect.top > viewport.bottom) return null;

                const nodeData = {
                    shadowRoot: isShadowHost,
                    isTopLevel: isShadowHost, // Mark shadow hosts as top level
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

                // Handle shadow DOM - mark host and process shadow content
                if (node.shadowRoot) {
                    nodeData.shadowRoot = true;  // Mark as shadow host
                    const shadowChildren = this.processShadowRoot(node.shadowRoot, options);
                    // Even if there are no shadow children, keep shadowRoot=true
                    nodeData.children.push(...(shadowChildren || []));
                }

                // Handle iframes
                if (node.nodeName.toLowerCase() === 'iframe') {
                    const iframeChildren = this.processIframe(node, options);
                    if (iframeChildren) {
                        nodeData.children.push(...iframeChildren);
                    }
                }

                // Process regular children
                for (const child of node.childNodes) {
                    const childData = this.buildDomTree(child, options);
                    if (childData) nodeData.children.push(childData);
                }

                if (highlightElements && this.isInteractive(node)) {
                    nodeData.highlightIndex = this.highlightIndex++;
                    if (nodeData.highlightIndex === focusElement) {
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
                    options
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
        next_index = max([0] + [node.highlight_index for node in self._get_all_nodes(element_tree)
                              if isinstance(node, DOMElementNode) and node.highlight_index is not None]) + 1

        def process_node(node: DOMBaseNode, next_idx: int) -> int:
            if isinstance(node, DOMElementNode):
                if node.highlight_index is not None:
                    selector_map[node.highlight_index] = node
                # Always include shadow hosts
                elif node.shadow_root:
                    selector_map[next_idx] = node
                    next_idx += 1

                for child in node.children:
                    next_idx = process_node(child, next_idx)
            return next_idx

        process_node(element_tree, next_index)
        return selector_map

    def _get_all_nodes(self, node: DOMBaseNode) -> list[DOMBaseNode]:
        """Helper to get all nodes in tree"""
        nodes = [node]
        if isinstance(node, DOMElementNode):
            for child in node.children:
                nodes.extend(self._get_all_nodes(child))
        return nodes

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
