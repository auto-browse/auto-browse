"""Browser initialization views"""
from enum import Enum

class BrowserError(Exception):
    """Base class for browser errors"""
    pass

class URLNotAllowedError(BrowserError):
    """Raised when trying to navigate to a URL that is not allowed"""
    pass
