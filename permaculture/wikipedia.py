"""Wikipedia API."""

import re
from functools import partial

import pandas as pd
from attrs import define

from permaculture.html import parse_tables
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


def get_companion_plants(wikipedia):
    """Get companion plants from Wikipedia and return a DataFrame."""
    text = wikipedia.get_text("List_of_companion_plants")
    tables = parse_tables(text, class_=lambda x: not x)
    multi_dfs = [pd.DataFrame(t) for t in tables]
    dfs = [
        df[category].assign(Category=category)
        for df in multi_dfs
        for category in [df.columns[0][0]]
    ]
    df = pd.concat(dfs, ignore_index=True)
    df["Helps"] = (
        df["Helps"]
        .apply(partial(re.sub, r"\[.+?\]", ""))
        .apply(partial(re.sub, r"\W+$", ""))
    )
    return df
