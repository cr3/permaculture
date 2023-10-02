"""Unit test for the location module."""

import pytest

from permaculture.location import (
    LocationPoint,
    LocationPolygon,
)


def test_location_point_sequence():
    """A point should behave like a sequence of lat and lon."""
    result = LocationPoint(0, 1)
    assert tuple(result) == (0, 1)


@pytest.mark.parametrize(
    "point, expected",
    [
        (LocationPoint(0, 0), 0),
        (LocationPoint(1, 0), 1),
        (LocationPoint(0, 1), 1),
        (LocationPoint(1, 1), 2),
    ],
)
def test_location_point_normsqr(point, expected):
    """The euclidean norm squared should use the latitude and longitude."""
    result = point.normsqr
    assert result == expected


@pytest.mark.parametrize(
    "point, other, expected",
    [
        (LocationPoint(0, 0), (0, 0), 0),
        (LocationPoint(0, 0), (1, 0), 111),
        (LocationPoint(0, 0), (0, 1), 111),
        (LocationPoint(0, 0), (1, 1), 157),
    ],
)
def test_location_point_distance(point, other, expected):
    """The distance between two points return the great-circle distance."""
    result = point.distance(other)
    assert int(result) == expected


@pytest.mark.parametrize(
    "point, other, expected",
    [
        (LocationPoint(0, 0), (0, 0), 0),
        (LocationPoint(1, 0), (1, 0), 1),
        (LocationPoint(0, 1), (0, 1), 1),
        (LocationPoint(1, 1), (1, 1), 2),
    ],
)
def test_location_point_dot(point, other, expected):
    """The dot product should use the latitude and longituide."""
    result = point.dot(other)
    assert result == expected


@pytest.mark.parametrize(
    "point, other, expected",
    [
        (LocationPoint(0, 0), (0, 0), (0, 0)),
        (LocationPoint(1, 0), (0, 1), (1, 1)),
        (LocationPoint(0, 1), (1, 0), (1, 1)),
        (LocationPoint(1, 1), (1, 1), (2, 2)),
    ],
)
def test_location_point_add(point, other, expected):
    """Adding two points should return the resulting point."""
    result = point + other
    assert result == expected


@pytest.mark.parametrize(
    "point, other, expected",
    [
        (LocationPoint(0, 0), (0, 0), (0, 0)),
        (LocationPoint(1, 0), (0, 1), (1, -1)),
        (LocationPoint(0, 1), (1, 0), (-1, 1)),
        (LocationPoint(1, 1), (1, 1), (0, 0)),
    ],
)
def test_location_point_sub(point, other, expected):
    """Subtracting two points should return the resulting point."""
    result = point - other
    assert result == expected


@pytest.mark.parametrize(
    "point, other, expected",
    [
        (LocationPoint(0, 0), 2, (0, 0)),
        (LocationPoint(1, 0), 2, (2, 0)),
        (LocationPoint(0, 1), 2, (0, 2)),
        (LocationPoint(1, 1), 2, (2, 2)),
    ],
)
def test_location_point_mul(point, other, expected):
    """Multiplying a point by a number should return the resulting point."""
    result = point * other
    assert result == expected


@pytest.mark.parametrize(
    "point, other, expected",
    [
        (LocationPoint(0, 0), 2, (0, 0)),
        (LocationPoint(2, 0), 2, (1, 0)),
        (LocationPoint(0, 2), 2, (0, 1)),
        (LocationPoint(2, 2), 2, (1, 1)),
    ],
)
def test_location_point_div(point, other, expected):
    """Dividing a point by a number should return the resulting point."""
    result = point / other
    assert result == expected


@pytest.mark.parametrize(
    "polygon, expected",
    [
        (
            LocationPolygon.from_points(
                [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]],
            ),
            1,
        ),
        (
            LocationPolygon.from_points(
                [[1, 6], [3, 1], [7, 2], [4, 4], [8, 5]],
            ),
            16.5,
        ),
        (
            LocationPolygon.from_points(
                [[1, 6], [3, 1], [7, 2], [4, 4], [8, 5], [1, 6]],
            ),
            16.5,
        ),
    ],
)
def test_location_polygon_area(polygon, expected):
    """The area should return the area of a simple polygon in a plane."""
    result = polygon.area
    assert result == expected


@pytest.mark.parametrize(
    "polygon, point, expected",
    [
        (
            LocationPolygon.from_points(
                [[0, 0], [0, 1], [1, 1], [1, 0]],
            ),
            (0, 0),
            True,
        ),
        (
            LocationPolygon.from_points(
                [[20, 10], [50, 125], [125, 90], [150, 10]],
            ),
            (75, 50),
            True,
        ),
        (
            LocationPolygon.from_points(
                [[20, 10], [50, 125], [125, 90], [150, 10]],
            ),
            (200, 50),
            False,
        ),
        (
            LocationPolygon.from_points(
                [[20, 10], [50, 125], [125, 90], [150, 10]],
            ),
            (35, 90),
            False,
        ),
        (
            LocationPolygon.from_points(
                [[20, 10], [50, 125], [125, 90], [150, 10]],
            ),
            (50, 10),
            True,
        ),
    ],
)
def test_location_polygon_contains(polygon, point, expected):
    """The polygon contains a point when it's inside the edges."""
    result = polygon.contains(point)
    assert result == expected


@pytest.mark.parametrize(
    "polygon, point, expected",
    [
        (LocationPolygon.from_points([[0, 0]]), (0, 0), (0, 0)),
        (LocationPolygon.from_points([[1, 1]]), (0, 0), (1, 1)),
        (LocationPolygon.from_points([[1, 1], [0, 0]]), (0, 0), (0, 0)),
        (LocationPolygon.from_points([[0, 0], [2, 0]]), (1, 1), (1, 0)),
    ],
)
def test_location_polygon_nearest(polygon, point, expected):
    """The nearest point to a polygon should be the expected point."""
    result = polygon.nearest(point)
    assert result == expected
