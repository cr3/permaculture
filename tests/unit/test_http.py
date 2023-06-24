"""Unit tests for the http module."""

from datetime import datetime, timedelta

import pytest
from attrs import Factory, define, field

from permaculture.http import (
    HTTPCache,
    parse_http_expiry,
    parse_http_timestamp,
)
from permaculture.storage import MemoryStorage


@define(frozen=True)
class StubRequestsPreparedRequest:
    """Stub Requests PreparedRequest object."""

    method: str = "GET"
    headers: dict = {}
    body: str = ""
    url: str = "http://www.test.com/"


@define(frozen=True)
class StubRequestsResponse:
    """Stub Requests Response object."""

    status_code: int = 200
    headers: dict = {}
    body: str = ""
    url: str = "http://www.test.com/"
    request: StubRequestsPreparedRequest = field(
        default=Factory(
            lambda self: StubRequestsPreparedRequest(url=self.url),
            takes_self=True,
        )
    )


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
            "Sun, 01 Mar 2020 15:00:00 GMT",
            datetime(2020, 3, 1, 15, 0),
            id="RFC 1123",
        ),
        pytest.param(
            "Sunday, 01-Mar-20 15:00:00 GMT",
            datetime(2020, 3, 1, 15, 0),
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


@pytest.fixture
def http_cache():
    """An HTTP cache with memory backend."""
    return HTTPCache(MemoryStorage())


def test_http_cache_200_responses(http_cache):
    """The HTTP cache should store 200 responses."""
    resp = StubRequestsResponse()

    assert http_cache.store(resp)


def test_http_cache_non_200_responses(http_cache):
    """The HTTP cache should not store non-200 responses."""
    resp = StubRequestsResponse(status_code=403)

    assert not http_cache.store(resp)


def test_http_cache_can_retrieve_responses(http_cache):
    """The HTTP cache can retrieve responses on 304."""
    resp = StubRequestsResponse()

    http_cache.store(resp)
    assert http_cache.handle_304(resp) is resp


def test_http_cache_if_modified_since_header(http_cache):
    """The HTTP cache can add the If-Modified-Since header."""
    resp = StubRequestsResponse(
        headers={
            "Date": "Sun, 01 Mar 2020 15:00:00 GMT",
        }
    )
    req = StubRequestsPreparedRequest()

    assert http_cache.store(resp)
    http_cache.retrieve(req)

    assert req.headers["If-Modified-Since"] == "Sun, 01 Mar 2020 15:00:00 GMT"


def test_http_cache_expires_header(http_cache):
    """The HTTP cache respects the Expires header."""
    resp = StubRequestsResponse(
        headers={
            "Date": "Sun, 01 Mar 2020 15:00:00 GMT",
            "Expires": "Sun, 01 Mar 2050 15:00:00 GMT",
        }
    )
    req = StubRequestsPreparedRequest()

    http_cache.store(resp)
    assert http_cache.retrieve(req) is resp


def test_expires_headers_invalidate(http_cache):
    resp1 = StubRequestsResponse(
        headers={
            "Date": "Sun, 06 Nov 1994 08:49:37 GMT",
            "Expires": "Sun, 06 Nov 1994 08:49:37 GMT",
        }
    )
    resp2 = StubRequestsResponse(
        headers={
            "Date": "Sun, 06 Nov 1994 08:49:37 GMT",
            "Expires": "Sun, 06 Nov 1994 08:00:00 GMT",
        }
    )

    assert not http_cache.store(resp1)
    assert not http_cache.store(resp2)


def test_expiry_of_expires(http_cache):
    resp = StubRequestsResponse(
        headers={
            "Date": "Sun, 06 Nov 1994 08:49:37 GMT",
            "Expires": "Sun, 04 Nov 2012 08:49:37 GMT",
        }
    )
    req = StubRequestsPreparedRequest()
    earlier = timedelta(seconds=-60)
    much_earlier = timedelta(days=-1)

    http_cache._storage[resp.url] = {
        "response": resp,
        "creation": datetime.utcnow() + much_earlier,
        "expiry": datetime.utcnow() + earlier,
    }

    assert http_cache.retrieve(req) is None
    assert len(http_cache._storage) == 0


def test_http_cache_inside_max_age(http_cache):
    """The HTTP cache should store inside Cache-Control max-age."""
    resp = StubRequestsResponse(headers={"Cache-Control": "max-age=3600"})
    assert http_cache.store(resp)

    req = StubRequestsPreparedRequest()
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
    """The HTTP cache should store with a query string and inside Cache-Control max-age."""
    resp = StubRequestsResponse(
        headers={"Cache-Control": "max-age=3600"},
        url="http://www.test.com/?a=b",
    )

    assert http_cache.store(resp)

    cached_resp = http_cache.handle_304(resp)
    assert cached_resp is resp


@pytest.mark.parametrize(
    "method",
    [
        "POST",
        "PUT",
        "DELETE",
        "CONNECT",
        "PATCH",
    ],
)
def test_http_cache_non_cacheable_methods(method, http_cache):
    """The HTTP cache should not cache some methods."""
    req = StubRequestsPreparedRequest(method=method)
    resp = StubRequestsResponse(request=req)

    assert not http_cache.store(resp)


@pytest.mark.parametrize(
    "method",
    [
        "POST",
        "PUT",
        "DELETE",
        "CONNECT",
        "PATCH",
    ],
)
def test_http_cache_invalidate_some_methods(method, http_cache):
    """The HTTP cache should invalidate some methods"""
    resp = StubRequestsResponse()
    assert http_cache.store(resp)

    req = StubRequestsPreparedRequest(method=method)
    assert http_cache.retrieve(req) is None

    assert len(http_cache._storage) == 0
