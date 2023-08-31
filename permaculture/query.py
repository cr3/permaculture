"""Permaculture query."""

import contextlib
import sys
from argparse import ArgumentParser, FileType

from appdirs import user_cache_dir
from nltk.stem.porter import PorterStemmer

from permaculture.logger import (
    LoggerHandlerAction,
    LoggerLevelAction,
    setup_logger,
)
from permaculture.serializer import SerializerAction
from permaculture.wikipedia import Wikipedia
from permaculture.wikipedia.companion import get_companion_plants


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

    stemmer = PorterStemmer()
    data["Common stem"] = data["Common name"].apply(stemmer.stem)
    import pdb; pdb.set_trace()

    with contextlib.suppress(BrokenPipeError):
        data[["Category", "Common name", "Common stem"]].to_csv(args.output)
