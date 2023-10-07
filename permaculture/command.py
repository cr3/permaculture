"""Permaculture command."""

import logging
import re
import sys
from argparse import ArgumentParser, FileType
from itertools import groupby

from appdirs import user_cache_dir
from attrs import evolve
from configargparse import ArgParser

from permaculture.data import (
    flatten,
    unflatten,
)
from permaculture.database import Database
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction
from permaculture.storage import StorageAction


def make_args_parser():
    """Make a parser for command-line arguments only."""
    args_parser = ArgumentParser()
    args_parser.add_argument(
        "--output",
        type=FileType("wb"),
        default=sys.stdout.buffer,
        help="output file (default stdout)",
    )
    args_parser.add_argument(
        "--serializer",
        action=SerializerAction,
    )
    command = args_parser.add_subparsers(
        dest="command",
        help="permaculture command",
    )
    command.add_parser(
        "companions",
        help="plant companions list",
    )
    lookup = command.add_parser(
        "lookup",
        help="lookup characteristics by scientific name",
    )
    lookup.add_argument(
        "names",
        metavar="name",
        nargs="*",
        help="scientific name to lookup",
    )
    lookup.add_argument(
        "--exclude",
        dest="excludes",
        default=["$"],
        action="append",
        help="exclude these characteristics from the output",
    )
    lookup.add_argument(
        "--include",
        dest="includes",
        default=[],
        action="append",
        help="only include these characteristics in the output",
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
    )
    config.add_argument(
        "--database",
        help="filter on a database",
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
    database = Database.load(config)

    match args.command:
        case "companions":
            data = {
                key: [related.scientific_name for _, related in pairs]
                for key, pairs in groupby(
                    database.companions(),
                    lambda pair: pair[0].scientific_name,
                )
            }
        case "lookup":
            content_type = args.serializer.default_content_type
            f = flatten if content_type == "text/csv" else unflatten
            exclude = re.compile("|".join(args.excludes), re.I)
            include = re.compile("|".join(args.includes), re.I)
            data = [
                {
                    k: v
                    for k, v in f(plant).items()
                    if include.match(k) and not exclude.match(k)
                }
                for plant in database.lookup(*args.names)
            ]
        case "search":
            data = [
                {plant.scientific_name: plant.common_names}
                for plant in database.search(args.name)
            ]
        case "store":
            storage = evolve(
                config.storage,
                serializer="application/octet-stream",
            )
            storage[args.key] = args.file.read()
            return
        case _:
            args_parser.error(f"Unsupported command: {args.command}")

    output, *_ = args.serializer.encode(data)
    args.output.write(output)
