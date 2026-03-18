"""Unit tests for the sqlite module."""

import pytest

from permaculture.sqlite import url_to_uri


@pytest.mark.parametrize(
    "url, expected_uri, expected_kwargs",
    [
        pytest.param(
            ":memory:",
            ":memory:",
            {},
            id="bare :memory:",
        ),
        pytest.param(
            "memory://",
            ":memory:",
            {},
            id="memory scheme",
        ),
        pytest.param(
            "memory://shared",
            "file::memory:?cache=shared",
            {"uri": True},
            id="memory shared",
        ),
        pytest.param(
            "memory://mydb",
            "file:mydb?mode=memory&cache=shared",
            {"uri": True},
            id="memory named",
        ),
        pytest.param(
            "sqlite:///data/test.db",
            "/data/test.db",
            {},
            id="sqlite scheme",
        ),
        pytest.param(
            "file:///data/test.db",
            "file:/data/test.db",
            {"uri": True},
            id="file scheme",
        ),
        pytest.param(
            "file:///data/test.db?cache=shared",
            "file:/data/test.db?cache=shared",
            {"uri": True},
            id="file scheme with query",
        ),
        pytest.param(
            "/data/test.db",
            "/data/test.db",
            {},
            id="bare path",
        ),
    ],
)
def test_url_to_uri(url, expected_uri, expected_kwargs):
    """url_to_uri should convert URLs to SQLite URIs."""
    uri, kwargs = url_to_uri(url)
    assert uri == expected_uri
    assert kwargs == expected_kwargs


def test_url_to_uri_unsupported_scheme():
    """url_to_uri should reject unsupported schemes."""
    with pytest.raises(ValueError, match="Unsupported scheme"):
        url_to_uri("postgres://localhost/db")
