"""Wikipedia API."""

from attrs import define

from permaculture.http import (
    HTTPCacheAdapter,
    HTTPCacheAll,
    HTTPClient,
)
from permaculture.storage import FileStorage, MemoryStorage


@define(frozen=True)
class Wikipedia:
    """Wikipedia API."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url, cache_dir=None):
        """Instantiate Wikipedia from URL."""
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        cache = HTTPCacheAll(storage)
        adapter = HTTPCacheAdapter(cache)
        client = HTTPClient(url, adapter=adapter)
        return cls(client)

    def get(self, action="query", **kwargs):
        params = {
            "format": "json",
            "redirects": 1,
            "action": action,
            **kwargs,
        }
        return self.client.get("", params=params).json()

    def get_text(self, page):
        data = self.get("parse", prop="text", page=page)
        return data["parse"]["text"]["*"]
