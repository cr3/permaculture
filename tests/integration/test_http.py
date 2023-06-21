"""Integration tests for the http module."""

import pytest
import requests

from permaculture.http import HTTPCacheAdapter


@pytest.fixture
def session():
    session = requests.Session()
    session.mount("http://", HTTPCacheAdapter())
    return session


def test_we_respect_304(session):
    r1 = session.get("http://httpbin.org/cache")
    r2 = session.get("http://httpbin.org/cache")

    assert r1 is r2


def test_we_respect_cache_control(session):
    r1 = session.get(
        "http://httpbin.org/response-headers",
        params={"Cache-Control": "max-age=3600"},
    )
    r2 = session.get(
        "http://httpbin.org/response-headers",
        params={"Cache-Control": "max-age=3600"},
    )

    assert r1 is r2


def test_we_respect_expires(session):
    r1 = session.get(
        "http://httpbin.org/response-headers",
        params={"Expires": "Sun, 06 Nov 2034 08:49:37 GMT"},
    )
    r2 = session.get(
        "http://httpbin.org/response-headers",
        params={"Expires": "Sun, 06 Nov 2034 08:49:37 GMT"},
    )

    assert r1 is r2


def test_we_respect_cache_control_2(session):
    r1 = session.get(
        "http://httpbin.org/response-headers",
        params={"Cache-Control": "no-cache"},
    )
    r2 = session.get(
        "http://httpbin.org/response-headers",
        params={"Cache-Control": "no-cache"},
    )

    assert r1 is not r2
