"""Strategy for calculating the priority."""

from functools import cached_property

from attrs import define, evolve, field

from permaculture.ipinfo import IPinfo
from permaculture.nominatim import Nominatim


@define(frozen=True)
class Priority:
    weight = 1.0


@define(frozen=True, slots=False)
class LocationPriority(Priority):
    query = field()
    nominatim = field(factory=Nominatim)
    ipinfo = field(factory=IPinfo)

    def with_cache(self, storage):
        nominatim = self.nominatim.with_cache(storage)
        ipinfo = self.ipinfo.with_cache(storage)
        return evolve(self, nominatim=nominatim, ipinfo=ipinfo)

    @cached_property
    def weight(self):
        multi = self.nominatim.multi_polygon(self.query)
        point = self.ipinfo.point()
        distance = multi.distance(point)
        return 1 / distance if distance > 1 else 1.0
