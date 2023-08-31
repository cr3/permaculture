"""Wikipedia companion plants."""

import contextlib
import re
import sys
from argparse import ArgumentParser, FileType
from functools import partial

import pandas as pd
from appdirs import user_cache_dir

from permaculture.html import parse_tables
from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction
from permaculture.wikipedia import Wikipedia


def get_companion_plants(wikipedia):
    """Get companion plants from Wikipedia and return a DataFrame."""
    text = wikipedia.get_text("List_of_companion_plants")
    tables = parse_tables(text, class_=lambda x: not x)
    multi_dfs = [pd.DataFrame(t) for t in tables]
    dfs = [
        df[category].assign(Category=category)
        for df in multi_dfs
        for category in [df.columns[0][0]]
    ]
    df = pd.concat(dfs, ignore_index=True)
    df["Helps"] = (
        df["Helps"]
        .apply(partial(re.sub, r"\[.+?\]", ""))
        .apply(partial(re.sub, r"\W+$", ""))
    )
    return df


def main(argv=None):
    """Entry point to the Wikipedia list of companion plants."""
    parser = ArgumentParser()
    parser.add_argument(
        "--api-url",
        default="https://en.wikipedia.org/w/api.php",
        help=(
            "URL to the Wikipedia list of companion plants "
            "(default %(default)s)"
        ),
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

    wikipedia = Wikipedia.from_url(args.api_url, args.cache_dir)
    data = get_companion_plants(wikipedia)

    with contextlib.suppress(BrokenPipeError):
        data[["Category", "Common name", "Helps"]].to_csv(args.output)
