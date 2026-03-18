"""SQLite URL-to-URI conversion utilities."""

import sqlite3

from yarl import URL


def url_to_uri(url: URL | str) -> tuple[str, dict]:
    """Convert a URL to a SQLite URI and ``sqlite3.connect`` kwargs."""
    raw = str(url)
    url = URL(raw)
    scheme = url.scheme

    # Single-letter schemes are Windows drive letters, not real schemes.
    if len(scheme) == 1:
        scheme = ""

    match scheme:
        case "memory":
            name = url.host or url.path.lstrip("/")

            match name:
                case "":
                    return ":memory:", {}

                case "shared":
                    return "file::memory:?cache=shared", {"uri": True}

                case _:
                    query = dict(url.query)
                    query.setdefault("mode", "memory")
                    query.setdefault("cache", "shared")

                    query_str = "&".join(f"{k}={v}" for k, v in query.items())
                    return f"file:{name}?{query_str}", {"uri": True}

        case "sqlite":
            return url.path, {}

        case "file":
            query = dict(url.query)
            uri = f"file:{url.path}"
            if query:
                query_str = "&".join(f"{k}={v}" for k, v in query.items())
                uri += f"?{query_str}"
            return uri, {"uri": True}

        case "":
            if raw in (":memory:",):
                return ":memory:", {}
            return raw, {}

        case _:
            raise ValueError(f"Unsupported scheme: {url.scheme}")


def connect(url: URL | str) -> sqlite3.Connection:
    """Open a SQLite connection from a URL."""
    uri, kwargs = url_to_uri(url)
    return sqlite3.connect(uri, check_same_thread=False, **kwargs)
