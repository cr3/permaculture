"""Cache providers."""
from abc import ABCMeta, abstractmethod
from pathlib import Path
from urllib.parse import quote

from attrs import define, field

from permaculture.serializer import Serializer


class Cache(metaclass=ABCMeta):
    """Base class for cache providers."""

    @abstractmethod
    def __len__(self):
        """Return the size of the cache."""

    @abstractmethod
    def retrieve(self, key: str, default: object = None) -> object:
        """Retrieve cached value for the given key or the default."""

    @abstractmethod
    def store(self, key: str, value: object) -> None:
        """Store value for the given key."""

    @abstractmethod
    def discard(self, key: str) -> None:
        """Discard the given key."""


@define(frozen=True)
class FileCache(Cache):
    """Lightweight implementation of `pytest.cache`.

    :param path: Base path to cache directory.
    :param serializer: Serializer, defaults to `json_serializer`
    """

    _cachedir: Path = field(converter=Path)
    serializer: Serializer = Serializer("application/x-pickle")

    def _key_to_path(self, key):
        path = self._cachedir / quote(key, "")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def __len__(self):
        return len(list(self._cachedir.iterdir()))

    def retrieve(self, key, default=None):
        """Read from file."""
        path = self._key_to_path(key)
        if path.exists():
            payload = path.read_bytes()
            return self.serializer.decode(payload)
        else:
            return default

    def store(self, key, value):
        """Write to file."""
        path = self._key_to_path(key)
        payload, *_ = self.serializer.encode(value)
        path.write_bytes(payload)

    def discard(self, key):
        """Unlink file."""
        self._key_to_path(key).unlink(missing_ok=True)


@define(frozen=True)
class MemoryCache(Cache):
    """Memory cache."""

    _memory: dict = field(factory=dict)

    def __len__(self):
        """Length of dict."""
        return len(self._memory)

    def retrieve(self, key, default=None):
        """Read from dict."""
        return self._memory.get(key, default)

    def store(self, key, value):
        """Write the value to dict."""
        self._memory[key] = value

    def discard(self, key):
        """Delete key from dict."""
        self._memory.pop(key, None)


@define(frozen=True)
class NullCache(Cache):
    """Null cache.

    This cache never stores a value and always retrieves the default value.
    """

    def __len__(self):
        """Return 0."""
        return 0

    def retrieve(self, key, default=None):
        """Return default."""
        return default

    def store(self, key, value):
        """Noop."""

    def discard(self, key):
        """Noop."""
