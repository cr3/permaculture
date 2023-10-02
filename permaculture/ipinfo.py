"""IP address information."""

from functools import partial

from attrs import define, evolve, field

from permaculture.http import HTTPSession
from permaculture.location import LocationPoint

IPINFO_ORIGIN = "https://ipinfo.io"


@define(frozen=True)
class IPinfo:
    session = field(factory=partial(HTTPSession, IPINFO_ORIGIN))

    def with_cache(self, storage):
        session = self.session.with_cache(storage)
        return evolve(self, session=session)

    def json(self, ip=None):
        """Get information about an IP.

        :param ip: Optional IP address, defaults to your IP.
        """
        path = f"/{ip}/json" if ip else "/json"
        return self.session.get(path).json()

    def point(self, ip=None):
        """Get the point for an IP.

        :param ip: Optional IP address, defaults to your IP.
        """
        json = self.json(ip)
        return LocationPoint(*json["loc"].split(","))
