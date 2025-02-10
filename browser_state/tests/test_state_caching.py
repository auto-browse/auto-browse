"""Tests for browser state caching functionality"""
import asyncio
import pytest
from playwright.async_api import Page
from browser_init.browser import Browser, BrowserConfig
from browser_state.models import BrowserState, ViewportState

@pytest.mark.asyncio
async def test_initial_cached_state():
    """Test that initial state is properly cached on session creation"""
    browser = Browser(BrowserConfig(headless=True))
    context = await browser.new_context()
    session = await context.get_session()

    # Initial state should be populated
    assert session.cached_state is not None
    assert isinstance(session.cached_state, BrowserState)

    # Verify expected properties
    assert session.cached_state.dom_tree is not None
    assert isinstance(session.cached_state.selector_map, dict)
    assert isinstance(session.cached_state.tabs, list)
    assert isinstance(session.cached_state.viewport, ViewportState)

    await browser.close()

@pytest.mark.asyncio
async def test_state_update_and_cache():
    """Test that state updates are properly cached"""
    browser = Browser(BrowserConfig(headless=True))
    context = await browser.new_context()

    # Navigate to a page
    page = await context.get_current_page()
    await page.goto("https://example.com")

    # Get state and verify it updates cache
    new_state = await context.get_state()
    session = await context.get_session()

    # Verify state is properly cached
    assert session.cached_state is not None
    assert session.cached_state == new_state
    assert session.cached_state.url.rstrip('/') == "https://example.com"
    assert len(session.cached_state.tabs) == 1
    assert session.cached_state.tabs[0].url.rstrip('/') == "https://example.com"

    await browser.close()

@pytest.mark.asyncio
async def test_vision_state_caching():
    """Test state caching with vision (screenshots) enabled"""
    browser = Browser(BrowserConfig(headless=True))
    context = await browser.new_context()
    page = await context.get_current_page()
    await page.goto("https://example.com")

    # Get state with vision enabled
    state = await context.get_state(use_vision=True)
    session = await context.get_session()

    # Verify screenshot is included in state
    assert session.cached_state is not None
    assert state.screenshot is not None
    assert session.cached_state.screenshot is not None
    assert session.cached_state.screenshot == state.screenshot

    await browser.close()

@pytest.mark.asyncio
async def test_multiple_pages_state():
    """Test state caching with multiple pages"""
    browser = Browser(BrowserConfig(headless=True))
    context = await browser.new_context()

    # Set up first page
    page1 = await context.get_current_page()
    await page1.goto("https://example.com")
    state1 = await context.get_state()

    # Create and navigate second page
    session = await context.get_session()
    page2 = await session.context.new_page()
    await page2.goto("https://www.google.com")
    session.current_page = page2
    state2 = await context.get_state()

    # Verify different URLs and tab count
    assert state1.url.rstrip('/') != state2.url.rstrip('/')
    assert len(state2.tabs) == 2
    assert state2.tabs[1].url.rstrip('/') == "https://www.google.com"

    # Only verify the most essential differences in state
    assert state1.title != state2.title  # Different page titles

    await browser.close()
