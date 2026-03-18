"""Testing fixtures.

The logger_handler fixture is automatically provided by this package,
it does not need to be imported in conftest.py explicitly.
"""

import logging

import pytest
from yarl import URL

from permaculture.logger import setup_logger
from permaculture.storage import Storage
from permaculture.testing.logger import LoggerHandler


@pytest.fixture
def file(tmpdir):
    url = URL.build(path=str(tmpdir))
    return Storage.from_url(url)


@pytest.fixture
def memory():
    url = URL.build(scheme="memory", path="/")
    return Storage.from_url(url)


@pytest.fixture
def sqlite():
    url = URL.build(scheme="sqlite", path=":memory:")
    return Storage.from_url(url)


@pytest.fixture(
    params=["memory", "file", "sqlite"],
)
def storage(request):
    """Storage fixture."""
    return request.getfixturevalue(request.param)


@pytest.fixture(autouse=True)
def logger_handler():
    """Logger handler fixture."""
    handler = LoggerHandler()
    setup_logger(logging.DEBUG, handler)
    try:
        yield handler
    finally:
        setup_logger()
