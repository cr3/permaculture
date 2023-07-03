"""USDA Food Data Central API."""

import contextlib
import logging
import sys
from argparse import ArgumentParser, FileType
from enum import StrEnum
from itertools import count

from appdirs import user_cache_dir
from attrs import define
from requests import HTTPError

from permaculture.action import enum_action
from permaculture.http import (
    HTTPCacheAdapter,
    HTTPCacheAll,
    HTTPClient,
)
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction
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
    """USDA Food Data Centra API."""

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


def main(argv=None):
    """Entry point to the USDA Food Data Central API."""
    parser = ArgumentParser()
    parser.add_argument(
        "--api-url",
        default="https://api.nal.usda.gov/fdc",
        help="URL to the USDA Food Data Central API (default %(default)s)",
    )
    parser.add_argument(
        "--api-key",
        help="KEY to the USDA Food Data Central API",
    )
    parser.add_argument(
        "--cache-dir",
        default=user_cache_dir("permaculture"),
        help="cache HTTP requests to directory (default %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=FileType("wb"),
        default=sys.stdout.buffer,
        help="output file (default stdout)",
    )
    parser.add_argument(
        "--serializer",
        action=SerializerAction,
    )
    parser.add_argument(
        "--log-file",
        action=LoggerHandlerAction,
    )
    parser.add_argument(
        "--log-level",
        action=LoggerLevelAction,
    )

    subparsers = parser.add_subparsers(title="commands", dest="command")
    food_parser = subparsers.add_parser("food")
    food_parser.add_argument(
        "fdc_id",
        type=int,
        help="Food Data Central identifier, e.g. 2341752",
    )
    food_parser.add_argument(
        "--format",
        action=enum_action(UsdaFdcFormat),
        default=UsdaFdcFormat.full,
        help="output format (default full)",
    )
    foods_parser = subparsers.add_parser("foods")
    foods_parser.add_argument(
        "fdc_ids",
        type=int,
        nargs="*",
        help="Food Data Central identifiers",
    )
    foods_parser.add_argument(
        "--format",
        action=enum_action(UsdaFdcFormat),
        default=UsdaFdcFormat.full,
        help="output format (default full)",
    )
    all_foods_parser = subparsers.add_parser("all-foods")
    all_foods_parser.add_argument(
        "--sort-by",
        action=enum_action(UsdaFdcSortBy),
        default=UsdaFdcSortBy.fdc_id,
        help="sort value (default fdc_id)",
    )
    all_foods_parser.add_argument(
        "--sort-order",
        action=enum_action(UsdaFdcSortOrder),
        default=UsdaFdcSortOrder.asc,
        help="sort order (default asc)",
    )

    args = parser.parse_args(argv)

    setup_logger(args.log_level, args.log_file)

    fdc = UsdaFdc.from_url(args.api_url, args.api_key, args.cache_dir)
    match args.command:
        case "food":
            data = fdc.food(args.fdc_id, args.format)
        case "foods":
            data = fdc.foods(args.fdc_ids, args.format)
        case "all-foods":
            data = list(
                all_foods(
                    fdc,
                    sort_by=args.sort_by,
                    sort_order=args.sort_order,
                )
            )
        case _:
            parser.error(f"Unsupported command: {args.command}")

    output, *_ = args.serializer.encode(data)
    with contextlib.suppress(BrokenPipeError):
        args.output.write(output)
