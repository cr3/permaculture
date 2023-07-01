"""USDA plants services."""

import contextlib
import sys
from argparse import ArgumentParser, FileType

from appdirs import user_cache_dir
from attrs import define

from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPClient
from permaculture.serializer import SerializerAction
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

    def characteristics_search(self) -> bytes:
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
        response = self.client.post("CharacteristicsSearch", json=payload)
        return response.json()

    def plant_profile(self, symbol):
        """Plant profile for a symbol."""
        response = self.client.get("PlantProfile", params={"symbol": symbol})
        return response.json()

    def plant_characteristics(self, Id):
        """Plant characteristics for an identifier."""
        response = self.client.get(f"PlantCharacteristics/{Id}")
        return response.json()


def all_characteristics(plants):
    search = plants.characteristics_search()
    return [
        {
            **{f"General/{k}": v for k, v in r.items()},
            **{
                "/".join(
                    [
                        c["PlantCharacteristicCategory"],
                        c["PlantCharacteristicName"],
                    ]
                ): c["PlantCharacteristicValue"]
                for c in plants.plant_characteristics(r["Id"])
            },
        }
        for r in search["PlantResults"]
    ]


def main(argv=None):
    """Entry point to the USDA plants service."""
    parser = ArgumentParser()
    parser.add_argument(
        "--api-url",
        default="https://plantsservices.sc.egov.usda.gov/api",
        help="URL to the USDA plants services API (default %(default)s)",
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
    subparsers = parser.add_subparsers(title="commands", dest="command")
    subparsers.add_parser("characteristics-search")
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
    subparsers.add_parser("all-characteristics")

    args = parser.parse_args(argv)

    plants = UsdaPlants.from_url(args.api_url, args.cache_dir)
    if args.command == "characteristics-search":
        data = plants.characteristics_search()
    elif args.command == "plant-profile":
        data = plants.plant_profile(args.symbol)
    elif args.command == "plant-characteristics":
        data = plants.plant_characteristics(args.id)
    elif args.command == "all-characteristics":
        data = all_characteristics(plants)
    else:
        parser.error(f"Unsupported command: {args.command}")

    output, *_ = args.serializer.encode(data)
    with contextlib.suppress(BrokenPipeError):
        args.output.write(output)
