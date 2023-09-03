"""USDA Food Data Central API."""

import logging
from enum import StrEnum
from itertools import count

from attrs import define
from requests import HTTPError

from permaculture.http import (
    HTTPCacheAdapter,
    HTTPCacheAll,
    HTTPClient,
)
from permaculture.storage import FileStorage, MemoryStorage

logger = logging.getLogger(__name__)


UsdaFdcFormat = StrEnum("UsdaFdcFormat", ["abridged", "full"])
UsdaFdcSortBy = StrEnum(
    "UsdaFdcSortBy",
    {
        "data_type": "dataType.keyword",
        "description": "lowercaseDescription.keyword",
        "fdc_id": "fdcId",
        "published_date": "publishedDate",
    },
)
UsdaFdcSortOrder = StrEnum("UsdaFdcSortOrder", ["asc", "desc"])


@define(frozen=True)
class UsdaFdc:
    """USDA Food Data Central API."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url, api_key, cache_dir=None):
        """Instantiate USDA Food Data Central from URL and API KEY."""
        headers = {"X-Api-Key": api_key}
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        cache = HTTPCacheAll(storage)
        adapter = HTTPCacheAdapter(
            cache,
            ["X-Ratelimit-Limit", "X-Ratelimit-Remaining"],
        )
        client = HTTPClient(url, headers=headers, adapter=adapter)
        return cls(client)

    def food(self, fdc_id, fmt=UsdaFdcFormat.full):
        """Retrieve a single food item."""
        response = self.client.get(
            f"v1/food/{fdc_id}",
            params={"format": fmt},
        )
        return response.json()

    def foods(self, fdc_ids, fmt=UsdaFdcFormat.full):
        """Retrieve a single food item."""
        payload = {
            "fdcIds": fdc_ids,
            "format": fmt,
        }
        response = self.client.post("v1/foods", json=payload)
        return response.json()

    def foods_list(
        self,
        page_size=200,
        page_number=0,
        sort_by=UsdaFdcSortBy.fdc_id,
        sort_order=UsdaFdcSortOrder.asc,
    ):
        """Retrieve a paged list of foods."""
        payload = {
            "pageSize": page_size,
            "pageNumber": page_number,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
        path = "v1/foods/list"
        response = self.client.post(path, json=payload)
        return response.json()


def all_foods(fdc, **kwargs):
    """Iterate over all foods."""
    for page_number in count(0):
        try:
            yield from fdc.foods_list(page_number=page_number, **kwargs)
        except HTTPError:
            break
