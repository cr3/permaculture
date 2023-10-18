"""Permaculture command."""

import logging
import re
import sys
from argparse import ArgumentParser, FileType
from itertools import groupby
from pathlib import Path

from appdirs import user_cache_dir
from attrs import evolve
from configargparse import ArgParser

from permaculture.data import (
    flatten,
    unflatten,
)
from permaculture.database import Databases
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction
from permaculture.storage import StorageAction

logger = logging.getLogger(__name__)


def make_args_parser():
    """Make a parser for command-line arguments only."""
    args_parser = ArgumentParser()
    command = args_parser.add_subparsers(
        dest="command",
        help="permaculture command",
    )
    command.add_parser(
        "companions",
        help="plant companions list",
    )
    command.add_parser(
        "help",
        help="show configuration help",
    )
    command.add_parser(
        "iterate",
        help="iterate over all scientific names",
    )
    command.add_parser(
        "list",
        help="list available databases",
    )
    lookup = command.add_parser(
        "lookup",
        help="lookup characteristics by scientific name",
    )
    lookup.add_argument(
        "names",
        metavar="name",
        nargs="+",
        help="scientific name to lookup",
    )
    lookup.add_argument(
        "-f",
        "--file",
        action="store_true",
        help="obtain patterns from given names",
    )
    lookup.add_argument(
        "--exclude",
        dest="excludes",
        default=["$"],
        action="append",
        help="exclude these characteristics",
    )
    lookup.add_argument(
        "--include",
        dest="includes",
        default=[],
        action="append",
        help="only include these characteristics",
    )
    search = command.add_parser(
        "search",
        help="search for the scentific name by common name",
    )
    search.add_argument(
        "name",
        help="common name to search",
    )
    store = command.add_parser(
        "store",
        help="store a file for a storage key",
    )
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
    return args_parser


def make_config_parser(config_files):
    """Make a parser for configuration files and command-line arguments."""
    config = ArgParser(
        default_config_files=config_files,
        add_help=False,
    )
    config.add_argument(
        "--output",
        type=FileType("wb"),
        default=sys.stdout.buffer,
        help="output file (default: stdout)",
    )
    config.add_argument(
        "--serializer",
        action=SerializerAction,
    )
    config.add_argument(
        "--database",
        dest="databases",
        default=[],
        action="append",
        help="regular on databases (default: all)",
    )
    config.add_argument(
        "--log-file",
        action=LoggerHandlerAction,
    )
    config.add_argument(
        "--log-level",
        action=LoggerLevelAction,
        default=logging.WARNING,
    )
    config.add_argument(
        "--storage",
        action=StorageAction,
        default=user_cache_dir("permaculture"),
    )
    nc = config.add_argument_group(
        "nc",
        "Natural Capital",
    )
    nc.add_argument(
        "--nc-username",
    )
    nc.add_argument(
        "--nc-password",
    )
    return config


def main(argv=None):
    """Entry point to the permaculture command."""
    config_parser = make_config_parser(["~/.permaculture", ".permaculture"])
    args_parser = make_args_parser()

    args, remaining = args_parser.parse_known_args(argv)
    config = config_parser.parse_args(remaining)

    setup_logger(config.log_level, config.log_file, name="permaculture")
    databases = Databases.load(config)

    match args.command:
        case "companions":
            data = {
                key: [related.scientific_name for _, related in pairs]
                for key, pairs in groupby(
                    databases.companions(),
                    lambda pair: pair[0].scientific_name,
                )
            }
        case "help":
            config_parser.print_help()
            sys.exit(0)
        case "iterate":
            data = [plant.scientific_name for plant in databases.iterate()]
        case "list":
            data = list(databases)
        case "lookup":
            content_type = config.serializer.default_content_type
            exclude = re.compile("|".join(args.excludes), re.I)
            include = re.compile("|".join(args.includes), re.I)
            f = flatten if content_type == "text/csv" else unflatten
            if args.file:
                names = [
                    name
                    for file in args.names
                    for name in Path(file).read_text().splitlines()
                ]
            else:
                names = args.names
            data = [
                {
                    k: v
                    for k, v in f(plant).items()
                    if include.match(k) and not exclude.match(k)
                }
                for plant in databases.lookup(*names)
            ]
        case "search":
            data = [
                {plant.scientific_name: plant.common_names}
                for plant in databases.search(args.name)
            ]
        case "store":
            storage = evolve(
                config.storage,
                serializer="application/octet-stream",
            )
            storage[args.key] = args.file.read()
            return
        case command:
            args_parser.error(f"Programming error for command: {command}")

    try:
        output, *_ = config.serializer.encode(data)
    except Exception as e:
        logger.debug(e, exc_info=True)
        args_parser.error(
            "Unsupported serializer"
            f" {config.serializer.default_content_type!r} for command:"
            f" {args.command}"
        )

    config.output.write(output)
