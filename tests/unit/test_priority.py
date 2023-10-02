"""Unit tests for the priority module."""

from unittest.mock import Mock

from permaculture.priority import LocationPriority
from permaculture.storage import null_storage


def test_location_priority_weight(unique):
    """The location priority weight should be 1 over the distance."""
    distance = unique("float")
    multi_polygon = Mock(distance=Mock(return_value=distance))
    nominatim = Mock(multi_polygon=Mock(return_value=multi_polygon))
    priority = LocationPriority(None, nominatim, Mock())
    result = priority.weight
    assert result == 1 / distance


def test_location_priority_with_cache():
    """The location priority should cache nominatim and ipinfo."""
    nominatim = Mock()
    ipinfo = Mock()
    LocationPriority(None, nominatim, ipinfo).with_cache(null_storage)
    nominatim.with_cache.assert_called_once_with(null_storage)
    ipinfo.with_cache.assert_called_once_with(null_storage)
