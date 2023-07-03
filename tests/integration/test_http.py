"""Integration tests for the http module."""

import pytest
import requests

from permaculture.http import HTTPCacheAdapter


@pytest.fixture
def session():
    session = requests.Session()
    session.mount("http://", HTTPCacheAdapter())
    return session


def test_respect_304(session):
    """The cache adapter should return the same response on 304."""
    r1 = session.get("http://httpbin.org/cache")
    r2 = session.get("http://httpbin.org/cache")

    assert r1 is r2


def test_respect_cache_control_max_age(session):
    """The cache adapter should return the same response within max-age."""
    r1 = session.get(
        "http://httpbin.org/response-headers",
        params={"Cache-Control": "max-age=3600"},
    )
    r2 = session.get(
        "http://httpbin.org/response-headers",
        params={"Cache-Control": "max-age=3600"},
    )

    assert r1 is r2


def test_respect_cache_control_no_cache(session):
    """The cache adapter should return the same response when no-cache."""
    r1 = session.get(
        "http://httpbin.org/response-headers",
        params={"Cache-Control": "no-cache"},
    )
    r2 = session.get(
        "http://httpbin.org/response-headers",
        params={"Cache-Control": "no-cache"},
    )

    assert r1 is not r2


def test_respect_expires(session):
    """The cache adapter should return the same response within expires."""
    r1 = session.get(
        "http://httpbin.org/response-headers",
        params={"Expires": "Sun, 01 Mar 2050 12:00:00 GMT"},
    )
    r2 = session.get(
        "http://httpbin.org/response-headers",
        params={"Expires": "Sun, 01 Mar 2050 12:00:00 GMT"},
    )

    assert r1 is r2
