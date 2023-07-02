"""Unit tests for the logger module."""
import json
import logging
import sys
from argparse import ArgumentParser
from contextlib import contextmanager
from io import StringIO

import pytest
from hamcrest import (
    assert_that,
    has_entries,
    has_properties,
    is_,
    matches_regexp,
)

from permaculture.logger import (
    JsonFormatter,
    LoggerFormatter,
    LoggerHandlerAction,
    LoggerLevelAction,
    logger_context,
    remove_log_context,
    set_log_context,
    setup_logger,
)

DATE_PATTERN = r"\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}"


@contextmanager
def logger_stream(formatter):
    """Context manager for a stream used by a logger handler at debug level."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)

    setup_logger(logging.DEBUG, handler, formatter)
    try:
        yield stream
    finally:
        setup_logger()


def test_logger_formatter_default():
    """The LoggerFormatter should include microseconds by default."""
    with logger_stream(LoggerFormatter()) as stream:
        message = "message"
        logging.debug(message)
        stream.seek(0)

        assert_that(
            stream.readline(),
            matches_regexp(f'{DATE_PATTERN} {"DEBUG":<7} root {message}\n'),
        )


def test_logger_formatter_non_root_logger():
    """The LoggerFormatter includes the name even for non-root loggers."""
    with logger_stream(LoggerFormatter()) as stream:
        message = "message"
        logger = logging.getLogger("deeply.nested.logger")
        logger.error(message)
        stream.seek(0)

        assert_that(
            stream.readline(),
            matches_regexp(
                f'{DATE_PATTERN} {"ERROR":<7} deeply.nested.logger {message}\n'
            ),
        )


def test_logger_formatter_custom_fmt():
    """The LoggerFormatter can take fmt as argument."""
    with logger_stream(LoggerFormatter(fmt="%(message)s")) as stream:
        message = "message"
        logging.info(message)
        stream.seek(0)

        assert_that(
            stream.readline(),
            f"{message}\n",
        )


def test_logger_formatter_custom_datefmt():
    """The LoggerFormatter can also take datefmt as argument."""
    with logger_stream(
        LoggerFormatter(datefmt="%a, %d %b %Y %H:%M:%S")
    ) as stream:
        date_pattern = r"\w{3}, \d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2}"
        message = "message"
        logging.info(message)
        stream.seek(0)

        assert_that(
            stream.readline(),
            matches_regexp(f'{date_pattern} {"INFO":<7} root {message}\n'),
        )


def test_json_formatter_default():
    """The JsonFormatter should include Level, Message, Name and Timestamp."""
    with logger_stream(JsonFormatter()) as stream:
        message = "message"
        logging.debug(message)
        stream.seek(0)

        assert_that(
            json.loads(stream.readline()),
            has_entries(
                Level="DEBUG",
                Message=message,
                Name="root",
                Timestamp=matches_regexp(DATE_PATTERN),
            ),
        )


def test_json_formatter_context():
    """The JsonFormatter should include context data."""
    with logger_stream(JsonFormatter()) as stream:
        message = "message"
        source = "source"
        with logger_context({"Source": source}):
            logging.debug(message)
        stream.seek(0)

        assert_that(
            json.loads(stream.readline()),
            has_entries(
                Level="DEBUG",
                Message=message,
                Name="root",
                Timestamp=matches_regexp(DATE_PATTERN),
                Source=source,
            ),
        )


def test_logger_handler_action_default():
    """A LoggerHandlerAction should default to stderr."""
    parser = ArgumentParser()
    parser.add_argument("--handler", action=LoggerHandlerAction)

    result = parser.parse_args([])

    assert_that(
        result,
        has_properties(
            handler=has_properties(
                stream=sys.stderr,
                formatter=is_(LoggerFormatter),
            )
        ),
    )


def test_logger_handler_action_stdout():
    """A LoggerHandlerAction should use stdout with -."""
    parser = ArgumentParser()
    parser.add_argument("--handler", action=LoggerHandlerAction)

    result = parser.parse_args(["--handler", "-"])

    assert_that(
        result,
        has_properties(
            handler=has_properties(
                stream=sys.stdout,
                formatter=is_(LoggerFormatter),
            )
        ),
    )


def test_logger_handler_action_file(tmpdir):
    """A LoggerHandlerAction should use file stream with a filename."""
    parser = ArgumentParser()
    parser.add_argument("--handler", action=LoggerHandlerAction)
    filename = str(tmpdir.join("test.log"))

    result = parser.parse_args(["--handler", filename])

    assert_that(
        result,
        has_properties(
            handler=has_properties(
                baseFilename=filename,
                formatter=is_(LoggerFormatter),
            )
        ),
    )


def test_logger_level_action_default():
    """A LoggerLevelAction should default to INFO."""
    parser = ArgumentParser()
    parser.add_argument("--level", action=LoggerLevelAction)

    result = parser.parse_args([])

    assert_that(result, has_properties(level=logging.INFO))


@pytest.mark.parametrize(
    "choice, level",
    [
        ("debug", logging.DEBUG),
        ("Debug", logging.DEBUG),
        ("DEBUG", logging.DEBUG),
    ],
)
def test_logger_level_action_valid_choice(choice, level):
    """A LoggerLevelAction should set on a valid choice."""
    parser = ArgumentParser()
    parser.add_argument("--level", action=LoggerLevelAction)

    result = parser.parse_args(["--level", choice])

    assert_that(result, has_properties(level=level))


def test_logger_level_action_invalid_choice():
    """A LoggerLevelAction should exit on an invalid choice."""
    parser = ArgumentParser()
    parser.add_argument("--level", action=LoggerLevelAction)

    with pytest.raises(SystemExit):
        parser.parse_args(["--level", "test"])


def test_logger_level_action_unsupported_choice():
    """A LoggerLevelAction should exit on an unsupported choice."""
    parser = ArgumentParser()
    parser.add_argument("--level", action=LoggerLevelAction, choices=["test"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--level", "test"])


@pytest.mark.parametrize(
    "level, records",
    [
        pytest.param(
            logging.ERROR,
            [
                has_properties(levelname="ERROR"),
            ],
            id="ERROR",
        ),
        pytest.param(
            logging.WARNING,
            [
                has_properties(levelname="ERROR"),
                has_properties(levelname="WARNING"),
            ],
            id="WARNING",
        ),
        pytest.param(
            logging.INFO,
            [
                has_properties(levelname="ERROR"),
                has_properties(levelname="WARNING"),
                has_properties(levelname="INFO"),
            ],
            id="INFO",
        ),
        pytest.param(
            logging.DEBUG,
            [
                has_properties(levelname="ERROR"),
                has_properties(levelname="WARNING"),
                has_properties(levelname="INFO"),
                has_properties(levelname="DEBUG"),
            ],
            id="DEBUG",
        ),
    ],
)
def test_setup_logger_level(level, records, logger_handler):
    """The log level should output expected records."""
    logger = setup_logger(level, logger_handler)
    logger.error("This is error")
    logger.warning("This is warning")
    logger.info("This is info")
    logger.debug("This is debug")

    result = logger_handler.records

    assert_that(result, records)


def test_setup_logger_formatter(logger_handler):
    message = "message"
    logger = setup_logger(logging.DEBUG, logger_handler, JsonFormatter())
    logger.debug(message)

    record = logger_handler.records[0]
    result = json.loads(logger_handler.format(record))

    assert_that(
        result,
        has_entries(
            Level="DEBUG",
            Message=message,
            Name="root",
            Timestamp=matches_regexp(DATE_PATTERN),
        ),
    )


def test_set_remove_log_context(logger_handler):
    """Logging context is set and removed from log entries."""
    logging.info("Test log0")
    set_log_context({"a": "1"})
    logging.info("Test log1")
    set_log_context({"b": "2"})
    logging.info("Test log2")

    # Remove the contexts
    remove_log_context("a")
    logging.info("Test log3")
    remove_log_context("b")
    logging.info("Test log4")

    assert_that(
        logger_handler.records,
        [
            has_properties(msg="Test log0"),
            has_properties(msg='[{"a": "1"}] Test log1'),
            has_properties(msg='[{"a": "1", "b": "2"}] Test log2'),
            has_properties(msg='[{"b": "2"}] Test log3'),
            has_properties(msg="Test log4"),
        ],
    )


def test_logger_context(logger_handler):
    """Logging contexts are added to log lines within the context only."""
    logging.info("Test log0")

    with logger_context({"a": "1"}):
        logging.info("Test log1")
        with logger_context({"b": "2"}):
            logging.info("Test log2")
            with logger_context({"a": "3"}):
                logging.info("Test log3")
        logging.info("Test log4")
    logging.info("Test log5")
    with logger_context({"a": "1", "b": "2"}):
        logging.info("Test log6")

    assert_that(
        logger_handler.records,
        [
            has_properties(msg="Test log0"),
            has_properties(msg='[{"a": "1"}] Test log1'),
            has_properties(msg='[{"a": "1", "b": "2"}] Test log2'),
            has_properties(msg='[{"a": "3", "b": "2"}] Test log3'),
            has_properties(msg='[{"a": "1"}] Test log4'),
            has_properties(msg="Test log5"),
            has_properties(msg='[{"a": "1", "b": "2"}] Test log6'),
        ],
    )
