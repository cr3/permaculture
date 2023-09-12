"""Database utilities."""

import re
from collections.abc import Callable
from typing import Any

from attrs import define, field

from permaculture.registry import registry_load
from permaculture.tokenizer import tokenize


class DatabaseElementNotFound(Exception):
    """Raised when a database element is not found."""


@define(frozen=True)
class DatabaseElement:
    database: str = field()
    scientific_name: str = field(converter=tokenize)
    common_names: list[str] = field(converter=lambda x: list(filter(None, x)))
    characteristics: dict[str, Any] = field()


class DatabasePlugin:

    def lookup(self, scientific_name: str) -> DatabaseElement:
        return None


@define(frozen=True)
class Database:
    cache_dir: str | None
    _databases: dict[str, DatabasePlugin]

    @classmethod
    def load(cls, cache_dir=None, registry=None):
        """Load databases from registry."""
        if registry is None or "databases" not in registry:
            registry = registry_load("databases", registry)

        databases = registry.get("databases", {})

        return cls(cache_dir, databases)

    def iterate(self):
        for database in self._databases.values():
            yield from database.iterate(self.cache_dir)

    def search(self, common_name):
        for element in self.iterate():
            if any(
                re.search(common_name, tokenize(n), re.I)
                for n in element.common_names
            ):
                yield element

    def lookup(self, scientific_name):
        not_found = True
        for element in self.iterate():
            if re.match(scientific_name, element.scientific_name, re.I):
                not_found = False
                yield element

        if not_found:
            raise DatabaseElementNotFound(scientific_name)
