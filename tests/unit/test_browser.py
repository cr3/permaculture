"""Unit tests for the browser module."""

from unittest.mock import Mock

import pytest
from hamcrest import assert_that, equal_to, is_

from permaculture.browser import (
    BrowserClient,
    BrowserResponse,
    BrowserSession,
)
from permaculture.storage import hash_request


def test_browser_session_get_navigates():
    """BrowserSession.get() should navigate to origin + path."""
    page = Mock()
    page.content.return_value = "<html>content</html>"
    BrowserSession("http://example.com", page).get("/path")

    page.goto.assert_called_once_with("http://example.com/path")


def test_browser_session_get_returns_page_content():
    """BrowserSession.get() should return page content as text."""
    page = Mock()
    page.content.return_value = "<html>content</html>"

    assert_that(
        BrowserSession("http://example.com", page).get("/path").text,
        equal_to("<html>content</html>"),
    )


def test_browser_session_get_cached():
    """BrowserSession.get() should return cached response without navigating."""
    page = Mock()
    cached = BrowserResponse("cached")
    storage = {hash_request("GET", "http://example.com/path"): cached}

    assert_that(
        BrowserSession("http://example.com", page, storage).get("/path"), is_(cached)
    )


def test_browser_session_get_stores_in_cache():
    """BrowserSession.get() should store the response in cache."""
    page = Mock()
    page.content.return_value = "<html>new</html>"
    storage = {}
    BrowserSession("http://example.com", page, storage).get("/path")

    assert_that(storage[hash_request("GET", "http://example.com/path")].text, equal_to("<html>new</html>"))


def test_browser_session_with_cache():
    """with_cache() should return a new session with the given storage."""
    page = Mock()
    new_storage = {}

    assert_that(
        BrowserSession("http://example.com", page).with_cache(new_storage).storage,
        is_(new_storage),
    )


def test_browser_client_get():
    """BrowserClient.get() should work end-to-end with page factory."""
    page = Mock()
    page.content.return_value = "<html>factory</html>"
    client = BrowserClient("http://example.com", page_factory=lambda: page)

    assert_that(client.get("/path").text, equal_to("<html>factory</html>"))


def test_browser_client_open_cleanup_on_error():
    """BrowserClient.open() should clean up even when an error occurs."""
    page = Mock()
    page.goto.side_effect = RuntimeError("navigation failed")
    client = BrowserClient("http://example.com", page_factory=lambda: page)

    with (
        pytest.raises(RuntimeError, match="navigation failed"),
        client.open() as session,
    ):
        session.get("/path")


def test_browser_client_with_cache():
    """BrowserClient.with_cache() should return new instance with given storage."""
    new_storage = {}

    assert_that(
        BrowserClient("http://example.com").with_cache(new_storage).storage,
        is_(new_storage),
    )


def test_browser_client_open_passes_storage():
    """BrowserClient.open() should pass storage to BrowserSession."""
    storage = {hash_request("GET", "http://example.com/cached"): BrowserResponse("hit")}
    page = Mock()
    client = BrowserClient(
        "http://example.com", page_factory=lambda: page, storage=storage
    )

    with client.open() as session:
        assert_that(session.get("/cached").text, equal_to("hit"))
