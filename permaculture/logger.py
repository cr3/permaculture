"""Logger to setup logging for consistent messages.

The root logger can be setup like this which typically happens in the main
entrypoint or in the lambda handler:

    >>> logger = setup_logger()
    >>> logger.name
    'root'

The setup can also be parameterized with a custom log level or log handler:

    >>> handler = LoggerHandlerAction.get_handler('-')
    >>> logger = setup_logger(logging.DEBUG, handler)

The logger is typically instantiated with the name of the module at the top
of source files:

    >>> log = logging.getLogger(__name__)

Then, that logger is used inside functions and methods to log messages:

    >>> from permaculture.testing.logger import logger_time
    >>> with logger_time():
    ...     log.info('created %(user)s', {'user': 'x'})
    1970-01-01 00:00:00.000000 INFO    permaculture.logger created x

It is also possible to add structured context information to the messages:

    >>> with logger_context({'lambda': 'x'}), logger_time():
    ...     log.warning('message')
    1970-01-01 00:00:00.000000 WARNING permaculture.logger [{"lambda": "x"}] message

The LoggerLevelAction provides argument defaults for the log level:

    >>> from argparse import ArgumentParser
    >>> parser = ArgumentParser()
    >>> action = parser.add_argument('--log-level', action=LoggerLevelAction)
    >>> args = parser.parse_args(['--log-level', 'debug'])
    >>> args.log_level == logging.DEBUG
    True

The LoggerHandlerAction also provides argument defaults for the log handler:

    >>> action = parser.add_argument('--log-file', action=LoggerHandlerAction)
    >>> args = parser.parse_args(['--log-file', '-'])
    >>> from logging import StreamHandler
    >>> isinstance(args.log_file, StreamHandler)
    True

The log level and log file can then be used to setup the root logger like this:

    >>> logger = setup_logger(args.log_level, args.log_file)
"""
import contextvars
import json
import logging
import sys
from contextlib import contextmanager
from datetime import datetime

from permaculture.action import SingleAction

DEFAULT_LEVEL = logging.INFO


class LoggerFormatter(logging.Formatter):
    """Logger formatter with sensible defaults."""

    converter = datetime.utcfromtimestamp

    def __init__(self, fmt=None, datefmt=None):
        """Initialize a formatter with default fmt and datefmt."""
        if fmt is None:
            fmt = "%(asctime)s %(levelname)-7s %(name)s %(message)s"
        if datefmt is None:
            datefmt = "%Y-%m-%d %H:%M:%S.%f"
        super().__init__(fmt, datefmt)

    def formatTime(self, record, datefmt=None):
        """Format time with support for microseconds."""
        ct = self.converter(record.created)
        return ct.strftime(datefmt)


class JsonFormatter(LoggerFormatter):
    """Logger formatter with sensible defaults."""

    def __init__(self, fmt=None, datefmt=None):
        """Initialize a formatter with default fmt and datefmt."""
        if fmt is None:
            fmt = "%(message)s"
        super().__init__(fmt, datefmt)

    def formatMessage(self, record):
        data = {
            "Level": record.levelname,
            "Message": record.msg,
            "Name": record.name,
            "Timestamp": self.formatTime(record, self.datefmt),
            **getattr(record, "ctx", {}),
        }

        return json.dumps(data)


class LoggerHandlerAction(SingleAction):
    """Argument action for a logger handler.

    Return a stream handler to stderr by default, a stream handler to
    stdout with '-' or a file handler.
    """

    metavar = "FILE"

    def __init__(self, option_strings, **kwargs):
        """Initialize logger handler defaults."""
        kwargs.setdefault("default", self.get_handler())
        kwargs.setdefault("metavar", self.metavar)
        kwargs.setdefault("help", "file to write the log (default stderr)")
        super().__init__(option_strings, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Set the values to a stream handler or a file handler."""
        handler = self.get_handler(values)

        super().__call__(parser, namespace, handler, option_string)

    @classmethod
    def get_handler(cls, name=None):
        """Get a logger handler by name with a formatter."""
        if name == "-":
            handler = logging.StreamHandler(sys.stdout)
        elif name:
            handler = logging.FileHandler(name)
        else:
            handler = logging.StreamHandler()

        formatter = LoggerFormatter()
        handler.setFormatter(formatter)

        return handler


class LoggerLevelAction(SingleAction):
    """Argument action for a logger level.

    Return a numeric value for the log level.
    """

    choices = ["debug", "info", "warning", "error", "critical"]
    default = DEFAULT_LEVEL
    metavar = "LEVEL"

    def __init__(self, option_strings, **kwargs):
        """Initialize logger level defaults."""
        kwargs.setdefault("choices", self.choices)
        kwargs.setdefault("default", self.default)
        kwargs.setdefault("metavar", self.metavar)
        kwargs.setdefault(
            "help",
            "{choices} (default {default})".format(
                choices=", ".join(kwargs["choices"]),
                default=logging.getLevelName(kwargs["default"]).lower(),
            ),
        )
        kwargs.setdefault("type", str.lower)
        super().__init__(option_strings, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Set the values to a numeric log level."""
        try:
            level = getattr(logging, values.upper())
        except AttributeError:
            parser.error(f"Unsupported log level: {values}")

        super().__call__(parser, namespace, level, option_string)


def setup_logger(level=DEFAULT_LEVEL, handler=None, formatter=None, name=None):
    """Set a Logger instance with a handler."""
    logger = logging.getLogger(name)
    for old_handler in logger.handlers[:]:
        old_handler.flush()
        old_handler.close()
        logger.removeHandler(old_handler)

    if formatter is None:
        formatter = LoggerFormatter()

    if handler is None:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


log_context_var = contextvars.ContextVar("log_context_var", default={})


def _log_context_cls(cls):
    """Extend the given class by giving it context awareness."""

    class LogRecordContext(cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.ctx = log_context_var.get()

        def getMessage(self):
            msg = super().getMessage()
            if self.ctx:
                s = json.dumps(self.ctx)
                msg = f"[{s}] {msg}"

            return msg

    return LogRecordContext


def _ensure_log_uses_context():
    """Ensure the set log record factory includes context information."""
    log_factory = logging.getLogRecordFactory()
    logging.setLogRecordFactory(_log_context_cls(log_factory))


def set_log_context(ctx):
    """Set context to all log records."""
    _ensure_log_uses_context()
    log_context_var.get().update(ctx)


def remove_log_context(key):
    """Remove a log context from all log records."""
    _ensure_log_uses_context()
    log_context_var.get().pop(key, None)


@contextmanager
def logger_context(ctx):
    """Context managed function to add log message context."""
    _ensure_log_uses_context()

    current = log_context_var.get().copy()
    current.update(ctx)
    token = log_context_var.set(current)

    try:
        yield
    finally:
        log_context_var.reset(token)
