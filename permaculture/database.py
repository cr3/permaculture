"""Database utilities."""

import re
from collections.abc import Iterator
from functools import reduce
from itertools import groupby
from operator import attrgetter

from attrs import define

from permaculture.data import (
    merge,
    merge_numbers,
    merge_strings,
)
from permaculture.registry import registry_load
from permaculture.tokenizer import tokenize


class DatabasePlant(dict):
    @property
    def scientific_name(self):
        return self["scientific name"]

    @property
    def common_names(self):
        common_name = self.get("common name", [])
        if not isinstance(common_name, list):
            common_name = [common_name]

        return [n for n in common_name if n]

    def with_database(self, name):
        """Add the database name to this plant."""
        self[f"database/{name}"] = True
        return self


DatabaseCompanion = tuple[DatabasePlant, DatabasePlant]


@define(frozen=True)
class DatabasePlugin:
    def companions(self, compatible: bool) -> Iterator[DatabaseCompanion]:
        """Plant companions list."""
        return []

    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over all plants."""
        return []

    def search(self, common_name: str) -> Iterator[DatabasePlant]:
        """Search for the scientific name by common name."""
        for plant in self.iterate():
            if any(
                re.search(common_name, tokenize(n), re.I)
                for n in plant.common_names
            ):
                yield plant

    def lookup(self, *scientific_names: str) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names."""
        tokens = [tokenize(n) for n in scientific_names]
        for plant in self.iterate():
            if plant.scientific_name in tokens:
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

    def companions(self, compatible=True) -> Iterator[DatabaseCompanion]:
        """Plant companions list."""
        for database in self.databases.values():
            yield from database.companions(compatible)

    def lookup(self, *scientific_names: str) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names in all databases."""
        return merge_plants(
            plant.with_database(name)
            for name, database in self.databases.items()
            for plant in database.lookup(*scientific_names)
        )

    def search(self, common_name: str) -> Iterator[DatabasePlant]:
        """Search for the scientific name by common name in all databases."""
        return merge_plants(
            plant.with_database(name)
            for name, database in self.databases.items()
            for plant in database.search(common_name)
        )


def merge_plants(plants: Iterator[DatabasePlant]) -> Iterator[DatabasePlant]:
    """Group plants by scientific name, merging numbers and strings."""
    keyfunc = attrgetter("scientific_name")
    return (
        DatabasePlant(merge_numbers(merge_strings(reduce(merge, p, {}))))
        for _, p in groupby(sorted(plants, key=keyfunc), keyfunc)
    )
