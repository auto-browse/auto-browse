"""Browser initialization views"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from browser_capture.views import DOMElementNode, SelectorMap

@dataclass
class TabInfo:
    """Information about a browser tab"""
    page_id: int
    url: str
    title: str

class BrowserError(Exception):
    """Base class for browser errors"""
    pass

class URLNotAllowedError(BrowserError):
    """Raised when trying to navigate to a URL that is not allowed"""
    pass

@dataclass
class BrowserState:
    """State of the browser"""
    element_tree: DOMElementNode
    selector_map: SelectorMap
    url: str
    title: str
    screenshot: Optional[str]
    tabs: List[TabInfo]
    pixels_above: int = 0
    pixels_below: int = 0

@dataclass
class BrowserStateHistory:
    """Browser state history for visualization"""
    url: str
    title: str
    tabs: List[TabInfo]
    interacted_element: List[str]
    screenshot: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'url': self.url,
            'title': self.title,
            'tabs': [{'page_id': t.page_id, 'url': t.url, 'title': t.title} for t in self.tabs],
            'interacted_element': self.interacted_element,
            'screenshot': self.screenshot,
        }
