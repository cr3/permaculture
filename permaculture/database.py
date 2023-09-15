"""Database utilities."""

import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
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


class DatabasePlugin(ABC):
    @abstractmethod
    def search(self, common_name: str) -> Iterator[DatabaseElement]:
        """Search for the scientific name by common name."""

    @abstractmethod
    def lookup(self, scientific_name: str) -> Iterator[DatabaseElement]:
        """Lookup characteristics by scientific name."""


class DatabaseIterablePlugin(DatabasePlugin):
    @abstractmethod
    def iterate(self, cache_dir) -> Iterator[DatabaseElement]:
        """Iterate over all plants."""

    def search(self, cache_dir, common_name) -> Iterator[DatabaseElement]:
        for element in self.iterate(cache_dir):
            if any(
                re.search(common_name, tokenize(n), re.I)
                for n in element.common_names
            ):
                yield element

    def lookup(self, cache_dir, scientific_name) -> Iterator[DatabaseElement]:
        for element in self.iterate(cache_dir):
            if re.match(scientific_name, element.scientific_name, re.I):
                yield element


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

    def search(self, common_name):
        """Search for the scientific name by common name in all databases."""
        for database in self._databases.values():
            yield from database.search(self.cache_dir, common_name)

    def lookup(self, scientific_name):
        """Lookup characteristics by scientific name in all databases."""
        not_found = True
        for database in self._databases.values():
            not_found = False
            yield from database.lookup(self.cache_dir, scientific_name)

        if not_found:
            raise DatabaseElementNotFound(scientific_name)
