"""Browser state models"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from browser_capture.views import DOMElementNode

@dataclass
class TabInfo:
    """Information about a browser tab"""
    page_id: int
    url: str
    title: str

@dataclass
class ViewportState:
    """State of the viewport"""
    pixels_above: int = 0
    pixels_below: int = 0
    width: int = 0
    height: int = 0

@dataclass
class BrowserState:
    """Complete browser state including DOM tree, tabs, and viewport"""
    url: str
    title: str
    dom_tree: DOMElementNode
    selector_map: Dict[int, DOMElementNode]
    tabs: List[TabInfo]
    viewport: ViewportState
    screenshot: Optional[str] = None  # Base64 encoded screenshot if requested
