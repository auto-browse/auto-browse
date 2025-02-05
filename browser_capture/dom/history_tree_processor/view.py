"""History tree processor views"""
from dataclasses import dataclass
from typing import Protocol, List

class HashedDomElement(Protocol):
    """Protocol for DOM elements that can be hashed"""
    tag_name: str
    attributes: dict[str, str]

@dataclass
class TreeProcessorBase:
    """Base class for tree processing"""
    @staticmethod
    def compare_attributes(attrs1: dict[str, str], attrs2: dict[str, str], key: str) -> bool:
        """Compare two attribute dictionaries by a specific key"""
        return attrs1.get(key) == attrs2.get(key)

    @staticmethod
    def get_common_attributes(attrs1: dict[str, str], attrs2: dict[str, str]) -> List[str]:
        """Get list of common attribute names between two dictionaries"""
        return list(set(attrs1.keys()) & set(attrs2.keys()))
