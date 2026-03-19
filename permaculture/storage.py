"""Storage providers."""

import logging
import os
from collections.abc import MutableMapping
from hashlib import md5
from pathlib import Path
from urllib.parse import quote, unquote

from appdirs import user_cache_dir
from attrs import define, field
from yarl import URL

from permaculture.action import SingleAction
from permaculture.registry import registry_load
from permaculture.serializer import Serializer, json_serializer
from permaculture.sqlite import connect as sqlite_connect

logger = logging.getLogger(__name__)

DEFAULT_STORAGE = user_cache_dir("permaculture")


class StorageAction(SingleAction):
    """Argument action for storage."""

    metavar = "URL"

    def __init__(self, option_strings, **kwargs):
        """Initialize storage defaults."""
        default = kwargs.pop("default", None)
        kwargs.setdefault("default", self.get_storage(default) if default else None)
        kwargs.setdefault("metavar", self.metavar)
        kwargs.setdefault("help", f"storage URL (default {default})")
        super().__init__(option_strings, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Set the values to a storage."""
        storage = self.get_storage(values)
        super().__call__(parser, namespace, storage, option_string)

    @classmethod
    def get_storage(cls, url):
        """Get storage from a URL."""
        return Storage.from_url(url)


def hash_request(method, url, body=None):
    """Hash an HTTP-like request into a storage key."""
    data = json_serializer.encode({"method": method, "url": url, "body": body})
    return md5(data).hexdigest()  # noqa: S324


@define(frozen=True, slots=False)
class Storage(MutableMapping):

    url: URL = field(converter=URL)

    @classmethod
    def from_env(cls, env=os.environ) -> "Storage":
        """Get Storage from the environment."""
        path = env.get("PERMACULTURE_STORAGE", DEFAULT_STORAGE)
        return cls.from_url(path)

    @classmethod
    def from_url(cls, url: URL | str, registry=None) -> "Storage":
        """Find plugin in the registry."""
        if registry is None or "storage" not in registry:
            registry = registry_load("storage")
        scheme = URL(url).scheme
        if not scheme or len(scheme) == 1:
            scheme = "file"
        storage_cls = registry["storage"][scheme]
        return storage_cls.from_url(url)


@define(frozen=True, slots=False)
class MemoryStorage(dict, Storage):
    """In-memory storage backed by a plain dict."""

    @classmethod
    def from_url(cls, url: URL | str) -> "MemoryStorage":
        """Create a MemoryStorage from a URL."""
        return cls(url)


@define(frozen=True)
class NullStorage(Storage):
    """Null storage."""

    @classmethod
    def from_url(cls, url: URL | str) -> "NullStorage":
        """Create a NullStorage from a URL."""
        return cls(url)

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


null_storage = NullStorage("null")


@define(frozen=True)
class FileStorage(Storage):
    """File storage.

    :param base_path: Base path for storing files.
    :param serializer: Serializer, defaults to `application/x-pickle`.
    """

    base_path: Path = field(converter=Path, kw_only=True)
    serializer: Serializer = field(
        default="application/x-pickle",
        converter=lambda x: (x if isinstance(x, Serializer) else Serializer.load(x)),
        kw_only=True,
    )

    @classmethod
    def from_url(cls, url: URL | str) -> "FileStorage":
        """Create a FileStorage from a URL."""
        if not isinstance(url, URL):
            # Hack to prevent Windows separators from being encoded.
            base_path = str(url).replace("\\", "/")
            url = URL(base_path)
        else:
            base_path = url.path

        return cls(url, base_path=base_path)

    @property
    def path(self) -> Path:
        path = self.url.path
        if self.url.host:  # Relative path.
            path = f"{self.url.host}{path}"
        if len(self.url.scheme) == 1:  # Windows drive letter.
            path = f"{self.url.scheme}:{path}"

        return Path(path)

    def key_to_path(self, key) -> Path:
        return self.path / quote(key, "")

    def path_to_key(self, path) -> str:
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
        return map(self.path_to_key, self.path.iterdir())

    def __len__(self):
        return sum(1 for _ in self)


@define(frozen=True)
class SqliteStorage(Storage):
    """Sqlite storage."""

    conn = field(kw_only=True)
    serializer: Serializer = field(
        default="application/x-pickle",
        converter=lambda x: (x if isinstance(x, Serializer) else Serializer.load(x)),
        kw_only=True,
    )

    @classmethod
    def from_url(cls, url: URL | str) -> "SqliteStorage":
        conn = sqlite_connect(url)
        conn.execute("CREATE TABLE IF NOT EXISTS storage (key, data)")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_storage_key ON storage (key)"
        )
        conn.commit()

        return cls(url, conn=conn)

    def __getitem__(self, key):
        cursor = self.conn.execute("SELECT data FROM storage WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            raise KeyError(key)

        return self.serializer.decode(row[0])

    def __setitem__(self, key, value):
        data, *_ = self.serializer.encode(value)
        self.conn.execute("INSERT INTO storage VALUES (?, ?)", (key, data))
        self.conn.commit()

    def __delitem__(self, key):
        cursor = self.conn.execute(
            "DELETE FROM storage WHERE key = ? RETURNING 1", (key,)
        )
        row = cursor.fetchone()
        if row is None:
            raise KeyError(key)

        self.conn.commit()

    def __iter__(self):
        cursor = self.conn.execute("SELECT key FROM storage")
        for row in cursor:
            yield row[0]

    def __len__(self):
        cursor = self.conn.execute("SELECT COUNT(key) FROM storage")
        row = cursor.fetchone()
        return row[0]
