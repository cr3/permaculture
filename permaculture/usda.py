"""USDA plants services."""

import sys
from argparse import ArgumentParser, FileType

from attrs import define
from appdirs import user_cache_dir

from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPClient
from permaculture.storage import FileStorage, MemoryStorage


@define(frozen=True)
class USDAPlants:
    """USDA plants services API."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url, cache_dir=None):
        """Instantiate USDA Plants from URL."""
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        cache = HTTPCacheAll(storage)
        adapter = HTTPCacheAdapter(cache)
        client = HTTPClient(url, adapter=adapter)
        return cls(client)

    def download(self, content_type="text/csv") -> bytes:
        """Download characteristics."""
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
            "CharacteristicsSearch/Download",
            json=payload,
            headers={
                "Accept": content_type,
            },
        )

        content = response.content
        if content_type == "text/csv":
            # Split first line that is not actually CSV.
            content = b"\n".join(content.splitlines()[1:])

        return content


def main(argv=None):
    """Entry point to the USDA plants services."""
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
        type=FileType("wb"),
        default=sys.stdout.buffer,
        help="output file, defaults to stdout",
    )
    subparsers = parser.add_subparsers(title="commands", dest="command")
    download = subparsers.add_parser("download")
    download.add_argument(
        "--content-type",
        default="text/csv",
        help="accepted content type, defaults to %(default)r",
    )

    args = parser.parse_args(argv)

    plants = USDAPlants.from_url(args.api_url, args.cache_dir)
    if args.command == "download":
        output = plants.download(args.content_type)
    else:
        parser.error(f"Unsupported command: {args.command}")

    args.output.write(output)
