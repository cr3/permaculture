"""Database utilities."""

import re
from abc import ABC, abstractmethod
from collections.abc import Iterator

from attrs import define

from permaculture.registry import registry_load
from permaculture.tokenizer import tokenize


class DatabasePlantNotFound(Exception):
    """Raised when a database element is not found."""


class DatabasePlant(dict):
    @property
    def scientific_name(self):
        return self["scientific name"]

    @property
    def common_names(self):
        if name := self["common name"]:
            return [name]
        else:
            return []


@define(frozen=True)
class DatabasePlugin(ABC):
    def companions(self, compatible: bool) -> Iterator[DatabasePlant]:
        """Plant companions list."""
        yield from []

    @abstractmethod
    def search(self, common_name: str) -> Iterator[DatabasePlant]:
        """Search for the scientific name by common name."""

    @abstractmethod
    def lookup(self, scientific_name: str) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific name."""


class DatabaseIterablePlugin(DatabasePlugin):
    @abstractmethod
    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over all plants."""

    def search(self, common_name: str) -> Iterator[DatabasePlant]:
        for plant in self.iterate():
            if any(
                re.search(common_name, tokenize(n), re.I)
                for n in plant.common_names
            ):
                yield plant

    def lookup(self, scientific_name: str) -> Iterator[DatabasePlant]:
        token = tokenize(scientific_name)
        for plant in self.iterate():
            if re.match(f"{token}$", plant.scientific_name, re.I):
                yield plant


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

    def companions(self, compatible=True):
        """Plant companions list."""
        for database in self.databases.values():
            yield from database.companions(compatible)

    def lookup(self, scientific_name: str):
        """Lookup characteristics by scientific name in all databases."""
        not_found = True
        for database in self.databases.values():
            not_found = False
            yield from database.lookup(scientific_name)

        if not_found:
            raise DatabasePlantNotFound(scientific_name)

    def search(self, common_name: str):
        """Search for the scientific name by common name in all databases."""
        for database in self.databases.values():
            yield from database.search(common_name)
