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


@define(frozen=True)
class DatabasePlugin(ABC):
    @abstractmethod
    def search(self, common_name: str) -> Iterator[DatabaseElement]:
        """Search for the scientific name by common name."""

    @abstractmethod
    def lookup(self, scientific_name: str) -> Iterator[DatabaseElement]:
        """Lookup characteristics by scientific name."""


class DatabaseIterablePlugin(DatabasePlugin):
    @abstractmethod
    def iterate(self) -> Iterator[DatabaseElement]:
        """Iterate over all plants."""

    def search(self, common_name: str) -> Iterator[DatabaseElement]:
        for element in self.iterate():
            if any(
                re.search(common_name, tokenize(n), re.I)
                for n in element.common_names
            ):
                yield element

    def lookup(self, scientific_name: str) -> Iterator[DatabaseElement]:
        for element in self.iterate():
            if re.match(scientific_name, element.scientific_name, re.I):
                yield element


@define(frozen=True)
class Database:
    databases: dict[str, DatabasePlugin]

    @classmethod
    def load(cls, config=None, registry=None):
        """Load databases from registry."""
        if registry is None or "databases" not in registry:
            registry = registry_load("databases", registry)

        databases = {
            k: v.from_config(config)
            for k, v in registry.get("databases", {}).items()
            if not config.database or config.database.lower() == k
        }

        return cls(databases)

    def lookup(self, scientific_name: str):
        """Lookup characteristics by scientific name in all databases."""
        not_found = True
        for database in self.databases.values():
            not_found = False
            yield from database.lookup(scientific_name)

        if not_found:
            raise DatabaseElementNotFound(scientific_name)

    def search(self, common_name: str):
        """Search for the scientific name by common name in all databases."""
        for database in self.databases.values():
            yield from database.search(common_name)
