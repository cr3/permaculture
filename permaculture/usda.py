"""USDA plants services."""

import contextlib
import sys
from argparse import ArgumentParser, FileType

from appdirs import user_cache_dir
from attrs import define

from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPClient
from permaculture.storage import FileStorage, MemoryStorage


@define(frozen=True)
class UsdaPlants:
    """USDA plants service."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url, cache_dir=None):
        """Instantiate USDA Plants from URL."""
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        cache = HTTPCacheAll(storage)
        adapter = HTTPCacheAdapter(cache)
        client = HTTPClient(url, adapter=adapter)
        return cls(client)

    def characteristics_search(self, content_type="text/csv") -> bytes:
        """Search characteristics."""
        payload = {
            "Text": None,
            "Field": None,
            "Locations": None,
            "Groups": None,
            "Durations": None,
            "GrowthHabits": None,
            "WetlandRegions": None,
            "NoxiousLocations": None,
            "InvasiveLocations": None,
            "Countries": None,
            "Provinces": None,
            "Counties": None,
            "Cities": None,
            "Localities": None,
            "ArtistFirstLetters": None,
            "ImageLocations": None,
            "Artists": None,
            "CopyrightStatuses": None,
            "ImageTypes": None,
            "SortBy": "sortSciName",
            "Offset": None,
            "FilterOptions": None,
            "UnfilteredPlantIds": None,
            "Type": "Characteristics",
            "TaxonSearchCriteria": None,
            "MasterId": -1,
        }
        response = self.client.post(
            "CharacteristicsSearch",
            json=payload,
            headers={
                "Accept": content_type,
            },
        )

        content = response.content.decode("utf-8")
        if content_type == "text/csv":
            # Strip first line that is not actually CSV.
            content = "\n".join(content.splitlines()[1:])

        return content

    def plant_profile(self, symbol):
        """Plant profile for a symbol."""
        response = self.client.get("PlantProfile", params={"symbol": symbol})
        return response.content.decode("utf-8")

    def plant_characteristics(self, Id):
        """Plant characteristics for an identifier."""
        response = self.client.get(f"PlantCharacteristics/{Id}")
        return response.content.decode("utf-8")


def main(argv=None):
    """Entry point to the USDA plants service."""
    parser = ArgumentParser()
    parser.add_argument(
        "--api-url",
        default="https://plantsservices.sc.egov.usda.gov/api",
        help="URL to the USDA plants services API, defaults to %(default)r",
    )
    parser.add_argument(
        "--cache-dir",
        default=user_cache_dir("permaculture"),
        help="cache HTTP requests to directory, defaults to %(default)r",
    )
    parser.add_argument(
        "--output",
        type=FileType("w"),
        default=sys.stdout,
        help="output file, defaults to stdout",
    )
    subparsers = parser.add_subparsers(title="commands", dest="command")
    characteristics_search = subparsers.add_parser("characteristics-search")
    characteristics_search.add_argument(
        "--content-type",
        choices=["text/csv", "application/json"],
        default="text/csv",
        help="download content type, defaults to %(default)r",
    )
    plant_profile = subparsers.add_parser("plant-profile")
    plant_profile.add_argument(
        "symbol",
        help="plant symbol, e.g. ABBA",
    )
    plant_characteristics = subparsers.add_parser("plant-characteristics")
    plant_characteristics.add_argument(
        "id",
        type=int,
        help="plant identifier, e.g. 15309",
    )

    args = parser.parse_args(argv)

    plants = UsdaPlants.from_url(args.api_url, args.cache_dir)
    if args.command == "characteristics-search":
        output = plants.characteristics_search(args.content_type)
    elif args.command == "plant-profile":
        output = plants.plant_profile(args.symbol)
    elif args.command == "plant-characteristics":
        output = plants.plant_characteristics(args.id)
    else:
        parser.error(f"Unsupported command: {args.command}")

    with contextlib.suppress(BrokenPipeError):
        args.output.write(output)
