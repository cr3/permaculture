"""Logger testing module."""

from contextlib import contextmanager
from datetime import datetime
from logging import Handler
from unittest.mock import patch


class LoggerHandler(Handler):
    """Logger handler for recording log messages."""

    def __init__(self):
        """Initialize an empty list of records."""
        super().__init__()
        self.records = []

    def emit(self, record):
        """Append to the list of records."""
        self.format(record)
        self.records.append(record)


@contextmanager
def logger_time(seconds=0.0):
    """Set the logger time to the given `seconds` within a context.

    :param seconds: Time as returned by `time.time()`.
    """
    with patch("logging.time.time") as mock_time:
        mock_time.return_value = seconds
        yield datetime.utcfromtimestamp(seconds)
