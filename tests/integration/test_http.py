"""Integration tests for the http module."""

import pytest

from permaculture.http import HTTPCache, HTTPSession
from permaculture.storage import MemoryStorage


@pytest.fixture
def session():
    storage = MemoryStorage()
    return HTTPSession("http://httpbin.org").with_cache(storage, HTTPCache)


def test_respect_304(session):
    """The cache adapter should return the same response on 304."""
    r1 = session.get("/cache")
    r2 = session.get("/cache")

    assert r1 is r2


def test_respect_cache_control_max_age(session):
    """The cache adapter should return the same response within max-age."""
    r1 = session.get(
        "/response-headers",
        params={"Cache-Control": "max-age=3600"},
    )
    r2 = session.get(
        "/response-headers",
        params={"Cache-Control": "max-age=3600"},
    )

    assert r1 is r2


def test_respect_cache_control_no_cache(session):
    """The cache adapter should return the same response when no-cache."""
    r1 = session.get(
        "/response-headers",
        params={"Cache-Control": "no-cache"},
    )
    r2 = session.get(
        "/response-headers",
        params={"Cache-Control": "no-cache"},
    )

    assert r1 is not r2


def test_respect_expires(session):
    """The cache adapter should return the same response within expires."""
    r1 = session.get(
        "/response-headers",
        params={"Expires": "Sun, 01 Mar 2050 12:00:00 GMT"},
    )
    r2 = session.get(
        "/response-headers",
        params={"Expires": "Sun, 01 Mar 2050 12:00:00 GMT"},
    )

    assert r1 is r2
