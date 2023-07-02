"""Integration tests for the testing logger module."""

import logging

from hamcrest import assert_that, has_properties

from permaculture.testing.logger import logger_time


def test_logger_time_default(logger_handler):
    """The default time in the context manager is 0.0."""
    with logger_time():
        logging.info("foo")

    assert_that(
        logger_handler.records,
        [
            has_properties(created=0),
        ],
    )


def test_logger_time_seconds(logger_handler):
    """The time can be passed in seconds."""
    seconds = 1.1
    with logger_time(seconds):
        logging.info("foo")

    assert_that(
        logger_handler.records,
        [
            has_properties(created=seconds),
        ],
    )
