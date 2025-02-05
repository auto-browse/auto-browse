(() => {
	let highlightIndex = 0;

	function getXPath(node) {
		if (!node || !node.nodeName) return "";

		let name = node.nodeName.toLowerCase();
		const parent = node.parentNode;

		if (!parent) {
			return name;
		}

		const siblings = parent.children;
		let siblingCount = 0;
		let siblingIndex = 0;

		for (let i = 0; i < siblings.length; i++) {
			const sibling = siblings[i];
			if (sibling.nodeName.toLowerCase() === name) {
				if (sibling === node) {
					siblingIndex = siblingCount;
				}
				siblingCount++;
			}
		}

		if (siblingCount > 1) {
			name += "[" + (siblingIndex + 1) + "]";
		}

		const parentPath = getXPath(parent);
		return parentPath ? parentPath + "/" + name : name;
	}

	function isElementVisible(element) {
		const style = window.getComputedStyle(element);
		const rect = element.getBoundingClientRect();

		return (
			style.display !== "none" &&
			style.visibility !== "hidden" &&
			style.opacity !== "0" &&
			rect.width > 0 &&
			rect.height > 0
		);
	}

	function isInteractive(element) {
		const interactiveTags = [
			"a",
			"button",
			"input",
			"select",
			"textarea",
			"summary"
		];
		const interactiveRoles = [
			"button",
			"link",
			"checkbox",
			"radio",
			"tab",
			"menuitem",
			"option"
		];

		if (interactiveTags.includes(element.tagName.toLowerCase())) return true;
		if (
			element.hasAttribute("role") &&
			interactiveRoles.includes(element.getAttribute("role").toLowerCase())
		)
			return true;
		if (element.hasAttribute("tabindex")) return true;
		if (element.hasAttribute("contenteditable")) return true;
		if (element.hasAttribute("onclick")) return true;
		if (element.tagName.toLowerCase() === "div" && element.hasAttribute("role"))
			return true;

		return false;
	}

	function buildTree(
		node,
		highlightElements = true,
		focusHighlightIndex = -1,
		viewportExpansion = 0
	) {
		if (!node) return null;

		// Skip script and style tags
		if (
			node.nodeName.toLowerCase() === "script" ||
			node.nodeName.toLowerCase() === "style"
		) {
			return null;
		}

		// Handle text nodes
		if (node.nodeType === 3) {
			const text = node.textContent.trim();
			if (!text) return null;
			return {
				type: "TEXT_NODE",
				text: text,
				isVisible: isElementVisible(node.parentElement)
			};
		}

		// Skip non-element nodes
		if (node.nodeType !== 1) return null;

		const isVisible = isElementVisible(node);
		const rect = node.getBoundingClientRect();
		const viewport = {
			top: -viewportExpansion,
			bottom: window.innerHeight + viewportExpansion,
			left: 0,
			right: window.innerWidth
		};

		// Skip invisible elements unless they're interactive
		if (!isVisible && !isInteractive(node)) return null;

		// Skip elements outside viewport expansion
		if (rect.bottom < viewport.top || rect.top > viewport.bottom) return null;

		// Build node data
		const nodeData = {
			tagName: node.nodeName.toLowerCase(),
			xpath: getXPath(node),
			attributes: {},
			isVisible: isVisible,
			isInteractive: isInteractive(node),
			children: []
		};

		// Add attributes
		for (let i = 0; i < node.attributes.length; i++) {
			const attr = node.attributes[i];
			nodeData.attributes[attr.name] = attr.value;
		}

		// Check for shadowRoot
		if (node.shadowRoot) {
			nodeData.shadowRoot = true;
		}

		// Add children
		for (const child of node.childNodes) {
			const childData = buildTree(
				child,
				highlightElements,
				focusHighlightIndex,
				viewportExpansion
			);
			if (childData) nodeData.children.push(childData);
		}

		// Add highlightIndex for interactive elements
		if (highlightElements && isInteractive(node)) {
			nodeData.highlightIndex = highlightIndex++;
			if (nodeData.highlightIndex === focusHighlightIndex) {
				nodeData.isTopElement = true;
			}

			// Add highlight overlay
			if (highlightElements) {
				node.setAttribute(
					"browser-user-highlight-id",
					`playwright-highlight-${nodeData.highlightIndex}`
				);
			}
		}

		return nodeData;
	}

	// Remove existing highlight container
	const existingContainer = document.getElementById(
		"playwright-highlight-container"
	);
	if (existingContainer) {
		existingContainer.remove();
	}

	// Process arguments
	const args = arguments[0] || {};
	const doHighlightElements =
		args.doHighlightElements !== undefined ? args.doHighlightElements : true;
	const focusHighlightIndex =
		args.focusHighlightIndex !== undefined ? args.focusHighlightIndex : -1;
	const viewportExpansion =
		args.viewportExpansion !== undefined ? args.viewportExpansion : 0;

	// Reset highlight index
	highlightIndex = 0;

	// Build and return tree
	return buildTree(
		document.documentElement,
		doHighlightElements,
		focusHighlightIndex,
		viewportExpansion
	);
})();
