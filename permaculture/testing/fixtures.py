"""Testing fixtures.

The logger_handler fixture is automatically provided by this package,
it does not need to be imported in conftest.py explicitly.
"""

import logging

import pytest

from permaculture.logger import setup_logger
from permaculture.testing.logger import LoggerHandler


@pytest.fixture(autouse=True)
def logger_handler():
    """Logger handler fixture."""
    handler = LoggerHandler()
    setup_logger(logging.DEBUG, handler)
    try:
        yield handler
    finally:
        setup_logger()
