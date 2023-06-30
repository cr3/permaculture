"""Unit tests for the http module."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from permaculture.http import (
    HTTP_CACHEABLE_METHODS,
    HTTP_METHODS,
    HTTP_UNCACHEABLE_METHODS,
    HTTPCache,
    HTTPCacheAll,
    HTTPClient,
    HTTPEntry,
    parse_http_expiry,
    parse_http_timestamp,
)

from .stubs import StubRequestsPreparedRequest, StubRequestsResponse

http_cache = pytest.fixture(lambda: HTTPCache())
"""An HTTP cache with memory backend."""

http_cache_all = pytest.fixture(lambda: HTTPCacheAll())
"""An HTTP cache all with memory backend."""


def test_parse_http_expiry_with_max_age():
    """The expiry should be the current time + max-age (in seconds)."""
    now = datetime.now()
    expiry = parse_http_expiry("max-age=10", now)
    assert expiry == now + timedelta(seconds=10)


def test_parse_http_expiry_without_max_age():
    """The expiry should be None when there is no max-age."""
    expiry = parse_http_expiry("no-cache", None)
    assert expiry is None


@pytest.mark.parametrize(
    "timestamp, expected",
    [
        pytest.param(
            "Sun, 01 Mar 2020 12:00:00 GMT",
            datetime(2020, 3, 1, 12, 0),
            id="RFC 1123",
        ),
        pytest.param(
            "Sunday, 01-Mar-20 12:00:00 GMT",
            datetime(2020, 3, 1, 12, 0),
            id="RFC 850",
        ),
    ],
)
def test_parse_http_timestamp(timestamp, expected):
    """A date timestamp should follow RFC 2616."""
    assert parse_http_timestamp(timestamp) == expected


def test_parse_http_timestamp_invalid():
    """An invalid date timestamp should return None."""
    assert parse_http_timestamp("test") is None


def test_http_cache_200_responses(http_cache):
    """The HTTP cache should store 200 responses."""
    resp = StubRequestsResponse(200)

    assert http_cache.store(resp)


def test_http_cache_non_200_responses(http_cache):
    """The HTTP cache should not store non-200 responses."""
    resp = StubRequestsResponse(403)

    assert not http_cache.store(resp)


def test_http_cache_can_retrieve_304_responses(http_cache):
    """The HTTP cache can retrieve responses on 304."""
    resp = StubRequestsResponse(200)

    http_cache.store(resp)
    assert http_cache.handle_304(resp) is resp


@pytest.mark.parametrize("method", HTTP_CACHEABLE_METHODS)
def test_http_cache_if_modified_since_header(method, http_cache):
    """The HTTP cache can add the If-Modified-Since header."""
    resp = StubRequestsResponse(
        headers={
            "Date": "Sun, 01 Mar 2020 12:00:00 GMT",
        }
    )
    req = StubRequestsPreparedRequest(method)

    assert http_cache.store(resp)
    http_cache.retrieve(req)

    assert req.headers["If-Modified-Since"] == "Sun, 01 Mar 2020 12:00:00 GMT"


@pytest.mark.parametrize("method", HTTP_CACHEABLE_METHODS)
def test_http_cache_expires_header(method, http_cache):
    """The HTTP cache respects the Expires header."""
    resp = StubRequestsResponse(
        headers={
            "Date": "Sun, 01 Mar 2020 12:00:00 GMT",
            "Expires": "Sun, 01 Mar 2050 12:00:00 GMT",
        }
    )
    req = StubRequestsPreparedRequest(method)

    assert http_cache.store(resp)
    assert http_cache.retrieve(req) is resp


@pytest.mark.parametrize(
    "headers",
    [
        {
            "Date": "Sun, 01 Mar 2020 12:00:00 GMT",
            "Expires": "Sun, 01 Mar 2020 12:00:00 GMT",
        },
        {
            "Date": "Sun, 01 Mar 2020 12:00:00 GMT",
            "Expires": "Sun, 01 Mar 2020 11:00:00 GMT",
        },
    ],
)
def test_http_cache_expires_headers_invalidate(headers, http_cache):
    """The HTTP cache should not store expired headers."""
    resp = StubRequestsResponse(headers=headers)

    assert not http_cache.store(resp)


@pytest.mark.parametrize("method", HTTP_CACHEABLE_METHODS)
def test_http_cache_expiry_of_expires(method, http_cache):
    """The HTTP cache should expires entries."""
    resp = StubRequestsResponse(
        headers={
            "Date": "Sun, 01 Mar 2020 12:00:00 GMT",
            "Expires": "Sun, 01 Mar 2020 13:00:00 GMT",
        }
    )
    req = StubRequestsPreparedRequest(method)
    earlier = timedelta(seconds=-60)
    much_earlier = timedelta(days=-1)

    http_cache.storage[resp.url] = HTTPEntry(
        resp,
        datetime.utcnow() + much_earlier,
        datetime.utcnow() + earlier,
    )

    assert http_cache.retrieve(req) is None
    assert len(http_cache.storage) == 0


@pytest.mark.parametrize("method", HTTP_CACHEABLE_METHODS)
def test_http_cache_inside_max_age(method, http_cache):
    """The HTTP cache should store inside Cache-Control max-age."""
    resp = StubRequestsResponse(headers={"Cache-Control": "max-age=3600"})
    assert http_cache.store(resp)

    req = StubRequestsPreparedRequest(method)
    assert http_cache.retrieve(req) is resp


def test_http_cache_outside_max_age(http_cache):
    """The HTTP cache should not store outside Cache-Control max-age."""
    resp = StubRequestsResponse(headers={"Cache-Control": "max-age=0"})

    assert not http_cache.store(resp)


def test_http_cache_no_cache(http_cache):
    """The HTTP cache should not store with Cache-Control no-cache."""
    resp = StubRequestsResponse(headers={"Cache-Control": "no-cache"})

    assert not http_cache.store(resp)


def test_http_cache_no_store(http_cache):
    """The HTTP cache should not store with Cache-Control no-store."""
    resp = StubRequestsResponse(headers={"Cache-Control": "no-store"})

    assert not http_cache.store(resp)


def test_http_cache_with_query_string(http_cache):
    """The HTTP cache should not store with a query string."""
    resp = StubRequestsResponse(url="http://www.test.com/?a=b")

    assert not http_cache.store(resp)


def test_http_cache_with_query_inside_max_age(http_cache):
    """
    The HTTP cache should store with a query string and inside
    Cache-Control max-age.
    """
    resp = StubRequestsResponse(
        headers={"Cache-Control": "max-age=3600"},
        url="http://www.test.com/?a=b",
    )

    assert http_cache.store(resp)

    cached_resp = http_cache.handle_304(resp)
    assert cached_resp is resp


@pytest.mark.parametrize("method", HTTP_UNCACHEABLE_METHODS)
def test_http_cache_non_cacheable_methods(method, http_cache):
    """The HTTP cache should not cache some methods."""
    req = StubRequestsPreparedRequest(method)
    resp = StubRequestsResponse(request=req)

    assert not http_cache.store(resp)


@pytest.mark.parametrize("method", HTTP_UNCACHEABLE_METHODS)
def test_http_cache_invalidate_some_methods(method, http_cache):
    """The HTTP cache should invalidate some methods."""
    resp = StubRequestsResponse()
    assert http_cache.store(resp)

    req = StubRequestsPreparedRequest(method)
    assert http_cache.retrieve(req) is None

    assert len(http_cache.storage) == 0


@pytest.mark.parametrize("method", HTTP_METHODS)
def test_http_cache_all_methods(method, http_cache_all):
    """The HTTP cache all should cache all methods."""
    req = StubRequestsPreparedRequest(method)
    resp = StubRequestsResponse(
        request=req,
        url="http://www.test.com",
    )

    assert http_cache_all.store(resp)


@pytest.mark.parametrize(
    "url1, url2",
    [
        ("http://www.test.com", "http://www.test.com?a=b"),
    ],
)
def test_http_cache_all_different_query(url1, url2, http_cache_all):
    """The HTTP cache all should cache different queries separately."""
    resp1 = StubRequestsResponse(url=url1)
    assert http_cache_all.store(resp1)

    resp2 = StubRequestsResponse(url=url2)
    assert http_cache_all.store(resp2)


@pytest.mark.parametrize(
    "headers1, headers2",
    [
        ({"test": "a"}, {"test": "b"}),
    ],
)
def test_http_cache_all_different_headers(headers1, headers2, http_cache_all):
    """The HTTP cache all should cache different headers separately."""
    req1 = StubRequestsPreparedRequest(headers=headers1)
    resp1 = StubRequestsResponse(request=req1)
    assert http_cache_all.store(resp1)

    req2 = StubRequestsPreparedRequest(headers=headers2)
    resp2 = StubRequestsResponse(request=req2)
    assert http_cache_all.store(resp2)


@pytest.mark.parametrize(
    "body1, body2",
    [
        ({"test": "a"}, {"test": "b"}),
    ],
)
def test_http_cache_all_different_body(body1, body2, http_cache_all):
    """The HTTP cache all should cache different bodies separately."""
    req1 = StubRequestsPreparedRequest(body=body1)
    resp1 = StubRequestsResponse(request=req1)
    assert http_cache_all.store(resp1)

    req2 = StubRequestsPreparedRequest(body=body2)
    resp2 = StubRequestsResponse(request=req2)
    assert http_cache_all.store(resp2)


@pytest.mark.parametrize(
    "body1, body2",
    [
        (
            b'{"a": "1", "b": "2"}',
            b'{"b": "2", "a": "1"}',
        ),
    ],
)
def test_http_cache_all_same_json_body(body1, body2, http_cache_all):
    """The HTTP cache all should cache same json bodies similarly."""
    req1 = StubRequestsPreparedRequest(
        method="POST",
        body=body1,
        headers={"content-type": "application/json"},
    )
    resp1 = StubRequestsResponse(request=req1)
    assert http_cache_all.store(resp1)

    req2 = StubRequestsPreparedRequest(
        method="POST",
        body=body2,
        headers={"content-type": "application/json"},
    )
    resp2 = StubRequestsResponse(request=req2)
    assert not http_cache_all.store(resp2)


def test_http_cache_all_retrieve_new_responses(http_cache_all):
    """The HTTP cache retrieve new responses as None."""
    req = StubRequestsPreparedRequest()

    assert not http_cache_all.retrieve(req)


def test_http_cache_all_can_retrieve_all_responses(http_cache_all):
    """The HTTP cache can retrieve all responses."""
    req = StubRequestsPreparedRequest()
    resp = StubRequestsResponse(200, request=req)

    http_cache_all.store(resp)
    assert http_cache_all.retrieve(req) is resp


def test_http_cache_all_can_retrieve_304_responses(http_cache_all):
    """The HTTP cache can retrieve responses on 304."""
    req = StubRequestsPreparedRequest()
    resp = StubRequestsResponse(200, request=req)

    http_cache_all.store(resp)
    assert http_cache_all.handle_304(req) is resp


@pytest.mark.parametrize("method", HTTP_METHODS)
def test_http_client_request(method):
    """The HTTP client request should append the path to the base URL."""
    session = Mock()
    client = HTTPClient("http://www.test.com", session)
    client.request(method, "a")
    session.request.assert_called_once_with(method, "http://www.test.com/a")


def test_http_client_get():
    """The HTTP client should map partial methods to request."""
    session = Mock()
    client = HTTPClient("http://www.test.com/a", session)
    client.get("b")
    session.request.assert_called_once_with("GET", "http://www.test.com/a/b")
