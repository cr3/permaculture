"""Unit tests for the nominatim module."""

from unittest.mock import Mock

import pytest

from permaculture.location import (
    LocationMultiPolygon,
    LocationNotFound,
    LocationPoint,
)
from permaculture.nominatim import Nominatim

from .stubs import StubRequestsResponse


def test_nominatim_with_cache():
    """Instantiating a Nominatim instance with cache should use the cache."""
    storage = {}
    session = Mock()
    Nominatim(session).with_cache(storage)
    session.with_cache.assert_called_once_with(storage)


def test_nominatim_search(unique):
    """Searching should GET with the given parameters."""
    query = unique("text")
    json = Mock(return_value=[{}])
    session = Mock(get=Mock(return_value=StubRequestsResponse(json=json)))
    Nominatim(session).search(q=query)
    session.get.assert_called_once_with(
        "/search",
        params={"q": query, "format": "json"},
    )


def test_nominatim_point():
    """A point should get the latitude and longitude."""
    json = Mock(return_value=[{"lat": "1.0", "lon": "2.0"}])
    session = Mock(get=Mock(return_value=StubRequestsResponse(json=json)))
    point = Nominatim(session).point(None)
    assert point == LocationPoint(1.0, 2.0)


def test_nominatim_point_error():
    """A point should raise when there is no data."""
    json = Mock(return_value=[])
    session = Mock(get=Mock(return_value=StubRequestsResponse(json=json)))
    with pytest.raises(LocationNotFound):
        Nominatim(session).point(None)


def test_nominatim_multi_polygon():
    """A multi polygon should get the coordinates."""
    feature = {"geometry": {"coordinates": [[[[1.0, 2.0]]]]}}
    json = Mock(return_value={"features": [feature]})
    session = Mock(get=Mock(return_value=StubRequestsResponse(json=json)))
    multi = Nominatim(session).multi_polygon(None)
    assert multi == LocationMultiPolygon.from_polygons([[[2.0, 1.0]]])


def test_nominatim_multi_polygon_error():
    """A multi polygon should raise when there is no data."""
    json = Mock(return_value={})
    session = Mock(get=Mock(return_value=StubRequestsResponse(json=json)))
    with pytest.raises(LocationNotFound):
        Nominatim(session).multi_polygon(None)
