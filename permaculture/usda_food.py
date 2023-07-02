"""USDA food service."""

import contextlib
import logging
import sys
from argparse import ArgumentParser, FileType
from enum import Enum
from itertools import count

from appdirs import user_cache_dir
from attrs import define
from requests import HTTPError

from permaculture.action import EnumAction
from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPClient
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction
from permaculture.storage import FileStorage, MemoryStorage

logger = logging.getLogger(__name__)


UsdaFoodSortBy = Enum(
    "UsdaFoodSortBy",
    {
        "data_type": "dataType.keyword",
        "description": "lowercaseDescription.keyword",
        "fdc_id": "fdcId",
        "published_date": "publishedDate",
    },
)
UsdaFoodSortOrder = Enum(
    "UsdaFoodSortOrder",
    {
        "asc": "asc",
        "desc": "desc",
    },
)


@define(frozen=True)
class UsdaFood:
    """USDA food service."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url, api_key, cache_dir=None):
        """Instantiate USDA food from URL and API KEY."""
        headers = {"X-Api-Key": api_key}
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        cache = HTTPCacheAll(storage)
        adapter = HTTPCacheAdapter(cache)
        client = HTTPClient(url, headers=headers, adapter=adapter)
        return cls(client)

    def list(  # noqa: A003
        self,
        page_size=200,
        page_number=0,
        sort_by=UsdaFoodSortBy.fdc_id,
        sort_order=UsdaFoodSortOrder.asc,
    ):
        """Receive a paged list of foods."""
        payload = {
            "pageSize": page_size,
            "pageNumber": page_number,
            "sort_by": sort_by.value,
            "sort_order": sort_order.value,
        }
        path = "v1/foods/list"
        response = self.client.post(path, json=payload)
        logger.debug(
            (
                "POST %(path)s: "
                "X-Ratelimit-Limit: %(limit)s, "
                "X-Ratelimit-Remaining: %(remaining)s"
            ),
            {
                "path": path,
                "limit": response.headers.get("X-Ratelimit-Limit"),
                "remaining": response.headers.get("X-Ratelimit-Remaining"),
            },
        )

        return response.json()


def list_all(food, **kwargs):
    """Iterate over all foods."""
    for page_number in count(0):
        try:
            yield from food.list(page_number=page_number, **kwargs)
        except HTTPError:
            break


def main(argv=None):
    """Entry point to the USDA food service."""
    parser = ArgumentParser()
    parser.add_argument(
        "--api-url",
        default="https://api.nal.usda.gov/fdc",
        help="URL to the USDA food services API (default %(default)s)",
    )
    parser.add_argument(
        "--api-key",
        help="KEY to the USDA food services API",
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
    list_parser = subparsers.add_parser("list-all")
    list_parser.add_argument(
        "--sort-by",
        action=EnumAction,
        type=UsdaFoodSortBy,
        default=UsdaFoodSortBy.fdc_id,
        help="sort value (default %(default)s)",
    )
    list_parser.add_argument(
        "--sort-order",
        action=EnumAction,
        type=UsdaFoodSortOrder,
        default=UsdaFoodSortOrder.asc,
        help="sort order (default %(default)s)",
    )

    args = parser.parse_args(argv)

    setup_logger(args.log_level, args.log_file)

    food = UsdaFood.from_url(args.api_url, args.api_key, args.cache_dir)
    match args.command:
        case "list-all":
            data = list(
                list_all(
                    food,
                    sort_by=args.sort_by,
                    sort_order=args.sort_order,
                )
            )
        case _:
            parser.error(f"Unsupported command: {args.command}")

    output, *_ = args.serializer.encode(data)
    with contextlib.suppress(BrokenPipeError):
        args.output.write(output)
