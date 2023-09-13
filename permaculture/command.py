"""Permaculture command."""

import sys
from argparse import ArgumentParser, FileType
from collections import defaultdict

from appdirs import user_cache_dir
from configargparse import ArgParser

from permaculture.database import Database
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction
from permaculture.storage import FileStorage


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
    lookup = command.add_parser(
        "lookup",
        help="lookup characteristics by scientific name",
    )
    lookup.add_argument(
        "name",
        help="scientific name to lookup",
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
        "--cache-dir",
        default=user_cache_dir("permaculture"),
        help="cache HTTP requests to directory (default %(default)s)",
    )
    config.add_argument(
        "--log-file",
        action=LoggerHandlerAction,
    )
    config.add_argument(
        "--log-level",
        action=LoggerLevelAction,
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
    database = Database.load(config.cache_dir)

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
            args_parser.error(f"Unsupported command: {args.command}")

    output, *_ = args.serializer.encode(data, "application/x-yaml")
    args.output.write(output)
