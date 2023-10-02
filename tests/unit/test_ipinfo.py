"""Unit tests for the ipinfo module."""

from unittest.mock import Mock

import pytest

from permaculture.ipinfo import IPinfo
from permaculture.location import LocationPoint

from .stubs import StubRequestsResponse


def test_ipinfo_with_cache():
    """Instantiating an IPinfo instance with cache should use the cache."""
    storage = {}
    session = Mock()
    IPinfo(session).with_cache(storage)
    session.with_cache.assert_called_once_with(storage)


@pytest.mark.parametrize(
    "ip, path",
    [
        (None, "/json"),
        ("1.2.3.4", "/1.2.3.4/json"),
    ],
)
def test_ipinfo_json(ip, path):
    """The IP json should GET with the given parameters."""
    json = Mock(return_value={})
    session = Mock(get=Mock(return_value=StubRequestsResponse(json=json)))
    IPinfo(session).json(ip)
    session.get.assert_called_once_with(path)


def test_ipinfo_point():
    """A point should get the loc."""
    json = Mock(return_value={"loc": "1.0,2.0"})
    session = Mock(get=Mock(return_value=StubRequestsResponse(json=json)))
    point = IPinfo(session).point(None)
    assert point == LocationPoint(1.0, 2.0)
