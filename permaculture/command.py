"""Permaculture command."""

import sys
from argparse import ArgumentParser, FileType
from collections import defaultdict

from appdirs import user_cache_dir

from permaculture.database import Database
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction
from permaculture.storage import FileStorage


def main(argv=None):
    """Entry point to the permaculture command."""
    parser = ArgumentParser()
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
    lookup = subparsers.add_parser("lookup")
    lookup.add_argument(
        "name",
        help="lookup the characteristics given a latin name",
    )
    search = subparsers.add_parser("search")
    search.add_argument(
        "name",
        help="search for latin names given a common name",
    )
    store = subparsers.add_parser("store")
    store.add_argument(
        "key",
        help="storage key",
    )
    store.add_argument(
        "file",
        type=FileType("rb"),
        default=sys.stdin.buffer,
        help="input file (default stdin)",
    )

    args = parser.parse_args(argv)

    setup_logger(args.log_level, args.log_file)
    database = Database.load(args.cache_dir)

    match args.command:
        case "lookup":
            data = {
                element.database: element.characteristics
                for element in database.lookup(args.name)
            }
        case "search":
            data = defaultdict(set)
            for element in database.search(args.name):
                data[element.scientific_name].update(element.common_names)
            data = {k: sorted(v) for k, v in data.items()}
        case "store":
            storage = FileStorage(args.cache_dir, "application/octet-stream")
            storage[args.key] = args.file.read()
            return
        case _:
            parser.error(f"Unsupported command: {args.command}")

    output, *_ = args.serializer.encode(data, "application/x-yaml")
    args.output.write(output)
