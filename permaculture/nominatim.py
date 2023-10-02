"""Geocoding data from OpenStreetMap."""

from functools import partial

from attrs import define, evolve, field

from permaculture.http import HTTPSession
from permaculture.location import (
    LocationMultiPolygon,
    LocationNotFound,
    LocationPoint,
)

NOMINATIM_ORIGIN = "https://nominatim.openstreetmap.org"


@define(frozen=True)
class Nominatim:
    """Nominatim uses OpenStreetMap data to find locations on Earth."""

    session = field(factory=partial(HTTPSession, NOMINATIM_ORIGIN))

    def with_cache(self, storage):
        session = self.session.with_cache(storage)
        return evolve(self, session=session)

    def search(self, **params):
        """Search nominatim with the given params."""
        params.setdefault("format", "json")
        return self.session.get("/search", params=params).json()

    def point(self, query):
        """Get the point of a place."""
        data = self.search(q=query)
        if not data:
            raise LocationNotFound(f"No data for {query!r}")

        # TODO: validate what happens when len(data) > 1
        first = data[0]
        return LocationPoint(first["lat"], first["lon"])

    def multi_polygon(self, query):
        """Get a multiple polygons around a place."""
        data = self.search(
            q=query,
            format="geojson",
            polygon_geojson="1",
        )
        if not data:
            raise LocationNotFound(f"No data for {query!r}")

        coordinates = data["features"][0]["geometry"]["coordinates"]
        # Geojson points use [longitude, latitude].
        # https://en.wikipedia.org/wiki/GeoJSON
        return LocationMultiPolygon.from_polygons(
            [
                [(point[1], point[0]) for point in poly]
                for multi in coordinates
                for poly in multi
            ]
        )
