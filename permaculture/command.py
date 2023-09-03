"""Permaculture command."""

import sys
from argparse import ArgumentParser, FileType

from appdirs import user_cache_dir

from permaculture.iterator import Iterator
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction


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
    search = subparsers.add_parser("search")
    search.add_argument(
        "name",
        help="search for latin names given a common name",
    )
    lookup = subparsers.add_parser("lookup")
    lookup.add_argument(
        "name",
        help="lookup the characteristics given a latin name",
    )

    args = parser.parse_args(argv)

    setup_logger(args.log_level, args.log_file)
    iterator = Iterator.load(args.cache_dir)

    match args.command:
        case "search":
            for element in iterator.search(args.name):
                output, *_ = args.serializer.encode(
                    (
                        f"{element.scientific_name}:"
                        f" {', '.join(element.common_names)}\n"
                    ),
                    "text/plain",
                )
                args.output.write(output)
        case "lookup":
            element = iterator.lookup(args.name)
            output, *_ = args.serializer.encode(element)
            args.output.write(output)
        case _:
            parser.error(f"Unsupported command: {args.command}")
