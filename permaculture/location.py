"""Location information.

A point has a latitude and a longitude:

    >>> point = LocationPoint(0, 0)
    >>> point
    LocationPoint(lat=0.0, lon=0.0)

A polygon has many points that delimit a shape:

    >>> poly = LocationPolygon.from_bbox(0, 0, 1, 1)
    >>> poly.area
    1.0

A multi polygon has many polygons that define many shapes:

    >>> poly2 = LocationPolygon.from_bbox(1, 1, 3, 3)
    >>> multi = LocationMultiPolygon.from_polygons([poly, poly2])
    >>> multi.area
    5.0

A point has a geographical distance to the nearest point on a polygon:

    >>> poly.distance(point)
    0
    >>> poly2.distance(point)
    157.24938127194397

A point also has a distance to the largest polygon, called the territory,
in a multi polygon:

    >>> multi.distance(point)
    157.24938127194397
"""

import sys
from collections.abc import Sequence
from functools import total_ordering
from itertools import pairwise
from math import asin, cos, radians, sin, sqrt

from attrs import define, field

EARTH_RADIUS = 6371

_huge = sys.float_info.max
_tiny = sys.float_info.min


class LocationNotFound(Exception):
    """Raised when a location is not found."""


@define(frozen=True)
class LocationPoint(Sequence):
    lat: float = field(converter=float)
    lon: float = field(converter=float)

    @classmethod
    def from_point(cls, point):
        if isinstance(point, cls):
            return point

        return cls(*point)

    def __len__(self):
        return 2

    def __getitem__(self, index):
        try:
            return {0: self.lat, 1: self.lon}[index]
        except KeyError:
            raise IndexError(index) from None

    @property
    def normsqr(self):
        """Euclidean norm squared."""
        return self.lat**2 + self.lon**2

    def distance(self, other):
        """Calculate the geographical distance between two points.

        Uses the haversine formula to determine the great-circle distance.
        """
        # Convert decimal degrees to radians.
        lat1, lon1 = map(radians, self)
        lat2, lon2 = map(radians, other)

        # Haversine formula.
        def hav(x):
            return sin(x / 2) ** 2

        x = hav(lat2 - lat1) + cos(lat1) * cos(lat2) * hav(lon2 - lon1)
        return 2 * EARTH_RADIUS * asin(sqrt(x))

    def dot(self, other):
        """Dot product."""
        other = LocationPoint.from_point(other)
        return self.lat * other.lat + self.lon * other.lon

    def slope(self, other):
        """Slope from this point to another point."""
        other = LocationPoint.from_point(other)
        if abs(other.lon - self.lon) > _tiny:
            return (other.lat - self.lat) / (other.lon - self.lon)
        else:
            return _huge

    def __eq__(self, other):
        other = LocationPoint.from_point(other)
        return self.lat == other.lat and self.lon == other.lon

    def __ne__(self, other):
        return not self == other

    def __add__(self, other):
        """LocationPoint + LocationPoint"""
        other = LocationPoint.from_point(other)
        return LocationPoint(self.lat + other.lat, self.lon + other.lon)

    def __radd__(self, other):
        """LocationPoint + LocationPoint"""
        other = LocationPoint.from_point(other)
        return LocationPoint(other.lat + self.lat, other.lon + self.lon)

    def __sub__(self, other):
        """LocationPoint - LocationPoint"""
        other = LocationPoint.from_point(other)
        return LocationPoint(self.lat - other.lat, self.lon - other.lon)

    def __rsub__(self, other):
        """LocationPoint - LocationPoint"""
        other = LocationPoint.from_point(other)
        return LocationPoint(other.lat - self.lat, other.lon - self.lon)

    def __mul__(self, other):
        """LocationPoint * number"""
        return LocationPoint(self.lat * other, self.lon * other)

    def __rmul__(self, other):
        """number * LocationPoint"""
        return LocationPoint(other * self.lat, other * self.lon)

    def __truediv__(self, other):
        """LocationPoint / number"""
        return LocationPoint(self.lat / other, self.lon / other)


@total_ordering
class LocationPolygonOrdering:
    def __lt__(self, other):
        """Order polygons by area."""
        return self.area < other.area


class LocationPolygon(LocationPolygonOrdering, list):
    """A polygon."""

    @classmethod
    def from_bbox(cls, west, south, east, north):
        points = [[west, south], [south, east], [east, north], [north, west]]
        return cls.from_points(points)

    @classmethod
    def from_points(cls, points):
        """Precalculate iedge vectors, for faster stable calculations"""
        points = map(LocationPoint.from_point, points)
        return cls(points)

    @property
    def area(self):
        """Return the area of the polygon."""
        # https://en.wikipedia.org/wiki/Shoelace_formula
        return abs(sum(b[0] * a[1] - b[1] * a[0] for a, b in self.pairs) / 2)

    @property
    def pairs(self):
        return [(a, b) for a, b in pairwise([self[-1], *self])]

    def contains(self, point):
        """Return whether this polygon contains a point."""
        # https://en.wikipedia.org/wiki/Point_in_polygon
        inside = False
        point = LocationPoint.from_point(point)
        for a, b in self.pairs:
            # Make sure A is the lower point of the edge
            if a.lat > b.lat:
                a, b = b, a

            # Check whether the horizontal ray intersects with the edge.
            if (
                point.lat > b.lat
                or point.lat < a.lat
                or point.lon > max(a.lon, b.lon)
            ):
                continue

            # Check whether the ray intersects with the edge.
            elif point.lon < min(a.lon, b.lon) or a.slope(point) >= a.slope(b):
                inside = not inside

        return inside

    def nearest(self, point):
        """Return the nearest point on the perimeter of the polygon."""
        # https://math.stackexchange.com/questions/4079605/how-to-find-closest-point-to-polygon-shape-from-any-coordinate
        nearest = None
        if self:
            nearest_normsqr = _huge

            for a, b in self.pairs:
                ab = b - a
                qq = ab.normsqr
                edge = ab / qq if qq > _tiny else [0, 0]

                t = (point - a).dot(edge)
                q = a if t <= 0 else (1 - t) * a + t * b if t < 1 else b
                qq = (q - point).normsqr
                if qq < nearest_normsqr:
                    nearest = q
                    nearest_normsqr = qq

        return nearest

    def distance(self, point):
        """Calculate the geographical distance to the nearest point."""
        if self.contains(point):
            return 0
        else:
            return self.nearest(point).distance(point)


class LocationMultiPolygon(list):
    """A multi polygon."""

    @classmethod
    def from_polygons(cls, polygons):
        polygons = map(LocationPolygon.from_points, polygons)
        return cls(polygons)

    @property
    def area(self):
        """Return the area of the multi polygon."""
        return sum(p.area for p in self)

    @property
    def territory(self):
        """Return the polygon with the largest area."""
        return max(self)

    def distance(self, point):
        """Calculate the geographical distance to the territory."""
        return self.territory.distance(point)
