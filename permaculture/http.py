"""HTTP module."""

from datetime import datetime, timedelta
from urllib.parse import urlparse

from attrs import define, field
from requests.adapters import HTTPAdapter

from permaculture.storage import MemoryStorage, Storage

RFC_1123_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
RFC_850_FORMAT = "%A, %d-%b-%y %H:%M:%S GMT"


def parse_http_expiry(header, current_time):
    """Parse HTTP cache-control into the corresponding expiry time (in UTC)."""
    for part in header.split(", "):
        if part.startswith("max-age"):
            _, n = part.split("=")
            return current_time + timedelta(seconds=int(n))


def parse_http_timestamp(header, default=None):
    """Parse an HTTP timestamp as RFC 2616."""
    try:
        return datetime.strptime(header, RFC_1123_FORMAT)
    except ValueError:
        try:
            return datetime.strptime(header, RFC_850_FORMAT)
        except ValueError:
            return default


CACHEABLE_STATUS_CODES = {200, 203, 300, 301, 410}
CACHEABLE_METHODS = {"GET", "HEAD", "OPTIONS"}


@define(frozen=True)
class HTTPCache:
    """Manages caching of responses according to RFC 2616."""

    _storage: Storage = field(factory=MemoryStorage)

    def store(self, response):
        """Store an HTTP response object in the cache."""

        if (
            response.status_code not in CACHEABLE_STATUS_CODES
            or response.request.method not in CACHEABLE_METHODS
        ):
            return False

        # Parse the date timestamp.
        now = datetime.utcnow()
        creation = parse_http_timestamp(response.headers.get("Date", ""), now)

        # Parse the expiry timestamp.
        cache_control = response.headers.get("Cache-Control")
        if cache_control is not None:
            expiry = parse_http_expiry(cache_control, now)
            if expiry is None:
                return False
        else:
            expiry = parse_http_timestamp(response.headers.get("Expires", ""))

        # If the expiry date is earlier or the same as the Date header, don't
        # cache the response at all.
        if expiry is not None and expiry <= creation:
            return False

        # If there's a query portion of the url and it's a GET, don't cache
        # this unless explicitly instructed to.
        if (
            expiry is None
            and response.request.method == "GET"
            and urlparse(response.url).query
        ):
            return False

        self._storage[response.url] = {
            "response": response,
            "creation": creation,
            "expiry": expiry,
        }

        return True

    def handle_304(self, response):
        """Given a 304 response, retrieve the cached entry."""
        cached_response = self._storage.get(response.url)
        if cached_response is None:
            return None

        return cached_response["response"]

    def retrieve(self, request):
        """Retrieve a cached HTTP response if possible."""
        url = request.url

        cached_response = self._storage.get(url)
        if cached_response is None:
            return None

        # If the method is not cacheable, remove from the cache.
        if request.method not in CACHEABLE_METHODS:
            del self._storage[url]
            return None

        # If we have no expiry time, add an 'If-Modified-Since' header.
        if cached_response["expiry"] is None:
            creation = cached_response["creation"]
            header = creation.strftime(RFC_1123_FORMAT)
            request.headers["If-Modified-Since"] = header
            return None

        # If we have an expiry time but it's later, remove from the cache.
        if datetime.utcnow() > cached_response["expiry"]:
            del self._storage[url]
            return None

        return cached_response["response"]


class HTTPCacheAdapter(HTTPAdapter):
    """An HTTP cache adapter for Python requests."""

    def __init__(self, cache, **kwargs):
        super().__init__(**kwargs)

        self.cache = HTTPCache(cache)

    def send(self, request, **kwargs):
        """Send a PreparedRequest object respecting RFC 2616 rules about HTTP caching."""
        cached_response = self.cache.retrieve(request)
        if cached_response is not None:
            return cached_response

        return super().send(request, **kwargs)

    def build_response(self, request, response):
        """Build a Response object from a urllib3 response."""
        resp = super().build_response(request, response)

        if resp.status_code == 304:
            resp = self.cache.handle_304(resp)
        else:
            self.cache.store(resp)

        return resp
