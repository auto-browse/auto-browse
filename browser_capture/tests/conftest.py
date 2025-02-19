"""Test configuration for browser_capture"""
import pytest

def pytest_configure(config):
    """Configure pytest"""
    # Register marks
    config.addinivalue_line(
        "markers", "asyncio: mark test as requiring asyncio"
    )
