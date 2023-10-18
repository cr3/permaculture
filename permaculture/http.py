"""HTTP module."""

import logging
from datetime import datetime, timedelta
from hashlib import md5
from urllib.parse import urlparse

from attrs import define, field
from requests import Response, Session
from requests.adapters import HTTPAdapter

from permaculture.serializer import json_serializer
from permaculture.storage import MemoryStorage, Storage

logger = logging.getLogger(__name__)


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


HTTP_METHODS = {
    "GET",
    "HEAD",
    "OPTIONS",
    "POST",
    "PUT",
    "DELETE",
    "CONNECT",
    "PATCH",
}
HTTP_CACHEABLE_METHODS = {"GET", "HEAD", "OPTIONS"}
HTTP_UNCACHEABLE_METHODS = HTTP_METHODS.difference(HTTP_CACHEABLE_METHODS)

HTTP_CACHEABLE_STATUS_CODES = {200, 203, 300, 301, 410}


@define(frozen=True)
class HTTPEntry:
    """HTTP entry to cache in storage."""

    response: Response
    creation: datetime
    expiry: datetime | None = None


@define(frozen=True)
class HTTPCache:
    """Manages caching of responses according to RFC 2616."""

    storage: Storage = field(factory=MemoryStorage)

    def store(self, response):
        """Store an HTTP response object in the cache."""

        if (
            response.status_code not in HTTP_CACHEABLE_STATUS_CODES
            or response.request.method not in HTTP_CACHEABLE_METHODS
        ):
            return False

        # Parse the date timestamp.
        now = datetime.utcnow()
        creation = parse_http_timestamp(response.headers.get("Date", ""), now)

        # Parse the expiry timestamp.
        if cache_control := response.headers.get("Cache-Control"):
            expiry = parse_http_expiry(cache_control, creation)
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

        self.storage[response.url] = HTTPEntry(response, creation, expiry)

        return True

    def handle_304(self, response):
        """Given a 304 response, retrieve the cached entry."""
        if entry := self.storage.get(response.url):
            return entry.response

        return None

    def retrieve(self, request):
        """Retrieve a cached HTTP response if possible."""
        url = request.url

        entry = self.storage.get(url)
        if entry is None:
            return None

        # If the method is not cacheable, remove from the cache.
        if request.method not in HTTP_CACHEABLE_METHODS:
            del self.storage[url]
            return None

        # If we have no expiry time, add an 'If-Modified-Since' header.
        if entry.expiry is None:
            modified_since = entry.creation.strftime(RFC_1123_FORMAT)
            request.headers["If-Modified-Since"] = modified_since
            return None

        # If we have an expiry time but it's later, remove from the cache.
        if datetime.utcnow() > entry.expiry:
            del self.storage[url]
            return None

        return entry.response


@define(frozen=True)
class HTTPCacheAll:
    """Manages caching of all responses."""

    storage: Storage = field(factory=MemoryStorage)

    def _hash_request(self, request):
        content_type = request.headers.get("content-type")
        if request.method == "POST" and content_type == "application/json":
            body = json_serializer.decode(request.body)
        else:
            body = request.body

        data = json_serializer.encode(
            {
                "method": request.method,
                "url": request.url,
                "body": body,
            }
        )
        return md5(data).hexdigest()  # noqa: S324

    def store(self, response):
        """Store an HTTP response object in the cache."""

        key = self._hash_request(response.request)
        if key in self.storage:
            return False

        # Parse the date timestamp.
        now = datetime.utcnow()
        creation = parse_http_timestamp(response.headers.get("Date", ""), now)
        self.storage[key] = HTTPEntry(response, creation)

        return True

    def retrieve(self, request):
        """Retrieve a cached HTTP response if possible."""
        key = self._hash_request(request)
        entry = self.storage.get(key)
        if entry is None:
            return None

        if "overwrite" in request.headers.get("X-Cache-All", ""):
            del self.storage[key]
            return None

        return entry.response

    handle_304 = retrieve


class HTTPCacheAdapter(HTTPAdapter):
    """An HTTP cache adapter for Python requests."""

    def __init__(self, cache, **kwargs):
        super().__init__(**kwargs)
        self.cache = cache

    def send(self, request, *args, **kwargs):
        """
        Send a PreparedRequest object respecting RFC 2616 rules about
        HTTP caching.
        """
        response = self.cache.retrieve(request)
        logger.debug(
            "cache %(verb)s: %(method)s %(url)s",
            {
                "method": request.method,
                "url": request.url,
                "verb": "hit" if response else "miss",
            },
        )

        if response is None:
            response = super().send(request, *args, **kwargs)

        return response

    def build_response(self, req, response):
        """Build a Response object from a urllib3 response."""
        resp = super().build_response(req, response)

        if resp.status_code == 304:
            resp = self.cache.handle_304(resp)
        else:
            self.cache.store(resp)

        return resp


class HTTPSession(Session):
    """An HTTP session with origin."""

    def __init__(self, origin, **kwargs):
        super().__init__(**kwargs)
        self.origin = origin

    def with_cache(self, storage, cache_cls=HTTPCacheAll, **kwargs):
        cache = cache_cls(storage)
        adapter = HTTPCacheAdapter(cache, **kwargs)
        return self.with_adapter(adapter)

    def with_adapter(self, adapter: HTTPAdapter):
        self.mount("https://", adapter)
        self.mount("http://", adapter)
        return self

    def request(self, method, path, **kwargs):
        """Send an HTTP request.

        :param method: Method for the request.
        :param path: Path joined to the URL.
        :param \\**kwargs: Optional keyword arguments passed to the session.
        """
        url = str(self.origin) + path
        response = super().request(method, url, **kwargs)
        response.raise_for_status()

        return response
