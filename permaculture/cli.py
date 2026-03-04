"""Permaculture CLI."""

import logging
import re
import sys
from argparse import ArgumentParser, FileType
from pathlib import Path

from appdirs import user_cache_dir
from attrs import evolve
from configargparse import ArgParser

from permaculture.data import (
    flatten,
    unflatten,
)
from permaculture.database import Database
from permaculture.ingestor import Ingestors
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.nlp import score_type
from permaculture.runner import Runner
from permaculture.serializer import SerializerAction
from permaculture.storage import StorageAction

logger = logging.getLogger(__name__)


def load_database(config):
    """Load the database from the configured storage."""
    db = Database.from_storage(config.storage)
    if not Path(db.db_path).exists():
        raise SystemExit(
            f"Database not found: {db.db_path}\n" "Run 'permaculture ingest' first."
        )
    return db


def make_args_parser():
    """Make a parser for command-line arguments only."""
    args_parser = ArgumentParser()
    command = args_parser.add_subparsers(
        dest="command",
        help="permaculture command",
    )
    command.add_parser(
        "help",
        help="show configuration help",
    )
    ingest = command.add_parser(
        "ingest",
        help="ingest plant data into local database",
    )
    ingest.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="maximum parallel source ingestions (default %(default)s)",
    )
    ingest.add_argument(
        "--retries",
        type=int,
        default=3,
        help="maximum retry attempts per source (default %(default)s)",
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
    lookup.add_argument(
        "--score",
        default=1.0,
        type=score_type,
        help="cutoff score (default %(default)s for exact match)",
    )
    search = command.add_parser(
        "search",
        help="search for the scentific name by common name",
    )
    search.add_argument(
        "name",
        help="common name to search",
    )
    search.add_argument(
        "--score",
        default=0.7,
        type=score_type,
        help="cutoff score (default %(default)s for partial match)",
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
        auto_env_var_prefix="PERMACULTURE_",
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
        "--ingestor",
        dest="ingestors",
        default=[],
        action="append",
        help="regex on ingestors (default: all)",
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
    nc.add_argument(
        "--nc-password-file",
    )
    return config


def command_ingest(args, config):
    """Ingest plant data into local database."""
    ingestors = Ingestors.load(config)
    db = Database.from_storage(config.storage)
    Runner(
        sources=dict(ingestors),
        database=db,
        max_concurrency=args.concurrency,
        max_retries=args.retries,
    ).run()


def command_iterate(database):
    """Iterate over all scientific names."""
    return [plant.scientific_name for plant in database.iterate()]


def command_list(database):
    """List available databases."""
    return database.sources()


def command_lookup(args, config, database):
    """Lookup characteristics by scientific name."""
    content_type = config.serializer.default_content_type
    exclude = re.compile("|".join(args.excludes), re.I)
    include = re.compile("|".join(args.includes), re.I)
    f = flatten if content_type == "text/csv" else unflatten
    if args.file:
        names = [
            name for file in args.names for name in Path(file).read_text().splitlines()
        ]
    else:
        names = args.names
    return [
        {k: v for k, v in f(plant).items() if include.match(k) and not exclude.match(k)}
        for plant in database.lookup(names, args.score)
    ]


def command_search(args, database):
    """Search for the scientific name by common name."""
    return [
        {plant.scientific_name: plant.common_names}
        for plant in database.search(args.name, args.score)
    ]


def command_store(args, config):
    """Store a file for a storage key."""
    storage = evolve(
        config.storage,
        serializer="application/octet-stream",
    )
    storage[args.key] = args.file.read()


def main(argv=None):
    """Entry point to the permaculture command."""
    config_parser = make_config_parser(["~/.permaculture", ".permaculture"])
    args_parser = make_args_parser()

    args, remaining = args_parser.parse_known_args(argv)
    config = config_parser.parse_args(remaining)

    setup_logger(config.log_level, config.log_file, name="permaculture")

    match args.command:
        case "help":
            config_parser.print_help()
            sys.exit(0)
        case "ingest":
            try:
                command_ingest(args, config)
            except ValueError as e:
                args_parser.error(str(e))
            return
        case "iterate":
            database = load_database(config)
            data = command_iterate(database)
        case "list":
            database = load_database(config)
            data = command_list(database)
        case "lookup":
            database = load_database(config)
            data = command_lookup(args, config, database)
        case "search":
            database = load_database(config)
            data = command_search(args, database)
        case "store":
            command_store(args, config)
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
