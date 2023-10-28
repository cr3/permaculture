"""Database utilities."""

import re
from collections.abc import Iterator
from itertools import groupby, starmap
from operator import attrgetter, mul

from attrs import define

from permaculture.data import merge
from permaculture.nlp import normalize
from permaculture.registry import registry_load


class DatabasePlant(dict):
    def __init__(self, data, weight=1.0):
        super().__init__(data)
        self.weight = weight

    @property
    def scientific_name(self):
        return self["scientific name"]

    @property
    def common_names(self):
        names = []
        for key in self:
            if m := re.match(r"common name/(?P<name>.+)", key):
                name = m.group("name")
                names.append(name)

        return names

    def with_database(self, name):
        """Add the database name to this plant."""
        self[f"database/{name}"] = True
        return self


DatabaseCompanion = tuple[DatabasePlant, DatabasePlant]


@define(frozen=True)
class Database:
    def companions(self, compatible: bool) -> Iterator[DatabaseCompanion]:
        """Plant companions list."""
        return []

    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over all plants."""
        return []

    def lookup(self, *scientific_names: str) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names."""
        normalized_names = [normalize(n) for n in scientific_names]
        for plant in self.iterate():
            if plant.scientific_name in normalized_names:
                yield plant

    def search(self, common_name: str) -> Iterator[DatabasePlant]:
        """Search for the scientific name by common name."""
        for plant in self.iterate():
            if any(
                re.search(common_name, normalize(n), re.I)
                for n in plant.common_names
            ):
                yield plant


class Databases(dict):
    @classmethod
    def load(cls, config=None, registry=None):
        """Load databases from registry."""
        if registry is None or "databases" not in registry:
            registry = registry_load("databases", registry)

        include = re.compile("|".join(config.databases), re.I)
        databases = {
            k: v.from_config(config)
            for k, v in registry.get("databases", {}).items()
            if include.match(k)
        }

        return cls(databases)

    def companions(self, compatible=True) -> Iterator[DatabaseCompanion]:
        """Plant companions list."""
        for database in self.values():
            yield from database.companions(compatible)

    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over plants."""
        return self.merge_all(
            plant.with_database(name)
            for name, database in self.items()
            for plant in database.iterate()
        )

    def lookup(self, *scientific_names: str) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names in all databases."""
        return self.merge_all(
            plant.with_database(name)
            for name, database in self.items()
            for plant in database.lookup(*scientific_names)
        )

    def search(self, common_name: str) -> Iterator[DatabasePlant]:
        """Search for the scientific name by common name in all databases."""
        return self.merge_all(
            plant.with_database(name)
            for name, database in self.items()
            for plant in database.search(common_name)
        )

    def merge_all(
        self, plants: Iterator[DatabasePlant]
    ) -> Iterator[DatabasePlant]:
        """Group plants by scientific name, merging numbers and strings."""
        keyfunc = attrgetter("scientific_name")
        return (
            DatabasePlant(self.merge(p))
            for _, p in groupby(sorted(plants, key=keyfunc), keyfunc)
        )

    def merge(self, plants: Iterator[DatabasePlant]) -> DatabasePlant:
        """Group plants by scientific name, merging numbers and strings."""
        plants = list(plants)

        # Resolve collisions using plant weights.
        def resolve(key, values):
            weights = [p.weight for p in plants if key in p]
            if isinstance(values[0], float | int):
                value = sum(
                    starmap(mul, zip(weights, values, strict=True))
                ) / sum(weights)
            else:
                _, value = max(zip(weights, values, strict=True))

            return value

        return merge(plants, resolve)
