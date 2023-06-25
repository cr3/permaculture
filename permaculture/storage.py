"""Storage providers."""
from collections.abc import MutableMapping
from pathlib import Path
from urllib.parse import quote, unquote

from attrs import define, field

from permaculture.serializer import Serializer

Storage = MutableMapping

MemoryStorage: Storage = dict


@define(frozen=True)
class FileStorage(Storage):
    """File storage.

    :param path: Base path to storage directory.
    :param serializer: Serializer, defaults to `json_serializer`
    """

    _basedir: Path = field(converter=Path)
    serializer: Serializer = Serializer.load("application/x-pickle")

    def _key_to_path(self, key):
        path = self._basedir / quote(key, "")
        return path

    def _path_to_key(self, path):
        return unquote(path.name)

    def __getitem__(self, key):
        """Read from file."""
        path = self._key_to_path(key)
        if not path.exists():
            raise KeyError(key)

        payload = path.read_bytes()
        return self.serializer.decode(payload)

    def __setitem__(self, key, value):
        """Write to file."""
        path = self._key_to_path(key)
        payload, *_ = self.serializer.encode(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def __delitem__(self, key):
        """Unlink file."""
        try:
            self._key_to_path(key).unlink()
        except FileNotFoundError as error:
            raise KeyError(key) from error

    def __iter__(self):
        return (self._path_to_key(p) for p in self._basedir.iterdir())

    def __len__(self):
        return sum(1 for _ in self)


@define(frozen=True)
class NullStorage(Storage):
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
