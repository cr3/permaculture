"""Design Ecologique resources web interface."""

import contextlib
import sys
from argparse import ArgumentParser, FileType

from appdirs import user_cache_dir
from attrs import define
from bs4 import BeautifulSoup
from yarl import URL

from permaculture.google.spreadsheets import GoogleSpreadsheet
from permaculture.http import HTTPClient
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction


@define(frozen=True)
class DesignEcologique:
    """Design Ecologique API."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url, cache_dir=None):
        """Instantiate Design Ecologique from URL."""
        client = HTTPClient.with_cache_all(url, cache_dir)
        return cls(client)

    def perenial_plants(self):
        response = self.client.get("liste-de-plantes-vivaces")
        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one("a[href*=spreadsheets]")
        if not element:
            raise KeyError("Link to Google spreadsheets not found")

        url = URL(element["href"])
        return GoogleSpreadsheet.from_url(url)


def main(argv=None):
    """Entry point to the USDA Food Data Central API."""
    parser = ArgumentParser()
    parser.add_argument(
        "--url",
        default="https://designecologique.ca",
        help="URL to the Design Ecologique website (default %(default)s)",
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

    args = parser.parse_args(argv)

    setup_logger(args.log_level, args.log_file)

    de = DesignEcologique.from_url(args.url, args.cache_dir)
    data = de.perenial_plants().export(1)

    output, *_ = args.serializer.encode(data)
    with contextlib.suppress(BrokenPipeError):
        args.output.write(output)
