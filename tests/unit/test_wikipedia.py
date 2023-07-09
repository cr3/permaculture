"""Unit tests for the wikipedia module."""

from unittest.mock import Mock

from permaculture.wikipedia import Wikipedia

from .stubs import StubRequestsResponse


def test_wikipedia_get():
    """The Wikipedia get method should GET with the given action."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    Wikipedia(client).get("test")
    client.get.assert_called_once_with(
        "",
        params={
            "format": "json",
            "redirects": 1,
            "action": "test",
        },
    )


def test_wikipedia_get_text():
    """The Wikipedia get text method should parse the page text."""
    client = Mock(
        get=Mock(
            return_value=StubRequestsResponse(
                json=lambda: {
                    "parse": {"text": {"*": "text"}},
                }
            )
        )
    )
    text = Wikipedia(client).get_text("page")
    client.get.assert_called_once_with(
        "",
        params={
            "format": "json",
            "redirects": 1,
            "action": "parse",
            "prop": "text",
            "page": "page",
        },
    )
    assert text == "text"
