"""Storage providers."""

import logging
from collections.abc import MutableMapping
from pathlib import Path
from urllib.parse import quote, unquote

from attrs import define, field

from permaculture.action import SingleAction
from permaculture.serializer import Serializer

logger = logging.getLogger(__name__)


class StorageAction(SingleAction):
    """Argument action for storage."""

    metavar = "PATH"

    def __init__(self, option_strings, registry=None, **kwargs):
        """Initializer storage defaults."""
        default = kwargs.pop("default", None)
        kwargs.setdefault("default", self.get_storage(default))
        kwargs.setdefault("metavar", self.metavar)
        kwargs.setdefault("help", f"storage path (default {default})")
        super().__init__(option_strings, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Set the values to a storage."""
        storage = self.get_storage(values)

        super().__call__(parser, namespace, storage, option_string)

    @classmethod
    def get_storage(cls, path):
        """Get storage with a default path."""
        return Storage.load(path)


class Storage(MutableMapping):
    @classmethod
    def load(cls, path=None):
        return FileStorage(path) if path else MemoryStorage()


MemoryStorage: Storage = dict


@define(frozen=True)
class FileStorage(Storage):
    """File storage.

    :param base_dir: Base directory for storing files.
    :param serializer: Serializer, defaults to `application/x-pickle`.
    """

    base_dir: Path = field(converter=Path)
    serializer: Serializer = field(
        default="application/x-pickle",
        converter=lambda x: (
            x if isinstance(x, Serializer) else Serializer.load(x)
        ),
    )

    def key_to_path(self, key):
        path = self.base_dir / quote(key, "")
        return path

    def path_to_key(self, path):
        return unquote(path.name)

    def __getitem__(self, key):
        """Read from file."""
        path = self.key_to_path(key)
        if not path.exists():
            raise KeyError(key)

        logger.debug("reading from %(path)s", {"path": path})
        payload = path.read_bytes()
        return self.serializer.decode(payload)

    def __setitem__(self, key, value):
        """Write to file."""
        path = self.key_to_path(key)
        payload, *_ = self.serializer.encode(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("writing to %(path)s", {"path": path})
        path.write_bytes(payload)

    def __delitem__(self, key):
        """Unlink file."""
        try:
            self.key_to_path(key).unlink()
        except FileNotFoundError as error:
            raise KeyError(key) from error

    def __iter__(self):
        return (self.path_to_key(p) for p in self.base_dir.iterdir())

    def __len__(self):
        return sum(1 for _ in self)


@define(frozen=True)
class _NullStorage(Storage):
    """Null storage.

    This storage stores a value and always retrieves the default value.
    """

    def __getitem__(self, key):
        """Raise KeyError."""
        raise KeyError(key)

    def __setitem__(self, key, value):
        """Noop."""

    def __delitem__(self, key):
        """Raise KeyError."""
        raise KeyError(key)

    def __iter__(self):
        yield from ()

    def __len__(self):
        """Return 0."""
        return 0


null_storage = _NullStorage()
