"""Process and compare DOM trees"""
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Optional

from browser_capture.views import DOMElementNode


@dataclass
class DOMHistoryElement:
    """Represents a DOM element in history with its key features"""
    tag_name: str
    attributes: dict[str, str]
    hash: str
    url: str
    text: str
    children: list['DOMHistoryElement']

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'tag_name': self.tag_name,
            'attributes': self.attributes,
            'hash': self.hash,
            'url': self.url,
            'text': self.text,
            'children': [child.to_dict() for child in self.children],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> 'DOMHistoryElement':
        """Create from dictionary"""
        return DOMHistoryElement(
            tag_name=data['tag_name'],
            attributes=data['attributes'],
            hash=data['hash'],
            url=data['url'],
            text=data['text'],
            children=[DOMHistoryElement.from_dict(child) for child in data['children']],
        )


class HistoryTreeProcessor:
    """Process and compare DOM trees"""

    @staticmethod
    def _get_text(element: DOMElementNode) -> str:
        """Get all text content from an element"""
        return element.get_all_text_till_next_clickable_element()

    @staticmethod
    def _hash_dom_element(element: DOMElementNode) -> str:
        """Create a hash of DOM element's key features"""
        features = [
            element.tag_name,
            str(sorted(element.attributes.items())),
            HistoryTreeProcessor._get_text(element),
        ]
        return hashlib.md5(''.join(features).encode()).hexdigest()

    @staticmethod
    def _are_attributes_similar(attrs1: dict, attrs2: dict, similarity_threshold: float = 0.8) -> bool:
        """Compare two sets of attributes for similarity"""
        if not attrs1 and not attrs2:
            return True
        if not attrs1 or not attrs2:
            return False

        common_keys = set(attrs1.keys()) & set(attrs2.keys())
        total_keys = set(attrs1.keys()) | set(attrs2.keys())

        if len(total_keys) == 0:
            return True

        # Compare values for common keys
        matching_values = sum(attrs1[key] == attrs2[key] for key in common_keys)
        similarity = (matching_values + len(common_keys)) / (2 * len(total_keys))

        return similarity >= similarity_threshold

    @staticmethod
    def find_history_element_in_tree(
        history_element: DOMHistoryElement,
        current_tree: DOMElementNode,
        similarity_threshold: float = 0.8,
    ) -> Optional[DOMElementNode]:
        """Find a history element in the current DOM tree"""
        if not isinstance(current_tree, DOMElementNode):
            return None

        # Compare tag name
        if history_element.tag_name != current_tree.tag_name:
            return None

        # Compare attributes
        if not HistoryTreeProcessor._are_attributes_similar(
            history_element.attributes, current_tree.attributes, similarity_threshold
        ):
            return None

        # Compare text content
        current_text = HistoryTreeProcessor._get_text(current_tree)
        if not HistoryTreeProcessor._is_text_similar(history_element.text, current_text, similarity_threshold):
            return None

        return current_tree

    @staticmethod
    def _is_text_similar(text1: str, text2: str, similarity_threshold: float = 0.8) -> bool:
        """Compare two text strings for similarity"""
        if not text1 and not text2:
            return True
        if not text1 or not text2:
            return False

        # Normalize texts
        text1 = re.sub(r'\s+', ' ', text1.strip())
        text2 = re.sub(r'\s+', ' ', text2.strip())

        # Simple exact match
        if text1 == text2:
            return True

        # For very short texts, require exact match
        if len(text1) < 10 or len(text2) < 10:
            return text1 == text2

        # Calculate similarity using difflib
        import difflib
        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        return similarity >= similarity_threshold
