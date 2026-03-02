"""Database utilities."""

import json
import re
import sqlite3
from collections.abc import Iterator, Mapping
from itertools import groupby, starmap
from operator import attrgetter, mul
from pathlib import Path

from attrs import define, field

from permaculture.data import merge
from permaculture.nlp import Extractor, normalize, score


@define(frozen=True, hash=False)
class DatabasePlant(Mapping):
    """Plant record with structured data and weight."""

    data: dict = field(factory=dict)
    weight: float = 1.0

    @property
    def scientific_name(self):
        return self.data.get("scientific name", "")

    @property
    def common_names(self):
        return [
            key.removeprefix("common name/")
            for key in self.data
            if key.startswith("common name/")
        ]

    @property
    def names(self):
        return [self.scientific_name, *self.common_names]

    def with_database(self, name):
        """Add the database name to this plant."""
        self.data[f"database/{name}"] = True
        return self

    def __getitem__(self, key):
        return self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


@define(frozen=True)
class Database:
    """Local database backed by a SQLite sink."""

    db_path: Path = field(converter=Path)

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _extract(self, query, choices):
        return Extractor(query, normalize, score).extract_one(choices)[0]

    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over all plants."""
        with self._connect() as conn:
            for data, weight in conn.execute(
                "SELECT data, weight FROM plants"
            ):
                yield DatabasePlant(json.loads(data), weight)

    def lookup(
        self, names: list[str], score: float
    ) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names."""
        if not names:
            return

        with self._connect() as conn:
            placeholders = ",".join("?" * len(names))
            for data, weight in conn.execute(
                "SELECT data, weight FROM plants"  # noqa: S608
                f" WHERE scientific_name IN ({placeholders})",
                names,
            ):
                yield DatabasePlant(json.loads(data), weight)

    def search(self, name: str, score: float) -> Iterator[DatabasePlant]:
        """Search for the scientific name by common name."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT p.data, p.weight"
                " FROM common_names cn"
                " JOIN plants p ON cn.plant_id = p.id"
                " WHERE cn.name LIKE ?",
                (f"%{name}%",),
            )
            for data, weight in rows:
                plant = DatabasePlant(json.loads(data), weight)
                if self._extract(name, plant.names) >= score:
                    yield plant


class Databases(dict):
    @classmethod
    def load(cls, config=None, registry=None):
        """Load databases from a local SQLite sink.

        Each database entry points to a Database backed by the same
        SQLite file, filtered by source name.
        """
        db_path = Path(config.storage.base_dir) / "permaculture.db"
        if not db_path.exists():
            return cls({})

        include = re.compile("|".join(config.databases), re.I)

        with sqlite3.connect(db_path) as conn:
            sources = [
                row[0]
                for row in conn.execute("SELECT DISTINCT source FROM plants")
            ]

        databases = {
            source: Database(db_path)
            for source in sources
            if include.match(source)
        }

        return cls(databases)

    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over plants."""
        return self.merge_all(
            plant.with_database(database_name)
            for database_name, database in self.items()
            for plant in database.iterate()
        )

    def lookup(self, names: str, score=1.0) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names in all databases."""
        return self.merge_all(
            plant.with_database(database_name)
            for database_name, database in self.items()
            for plant in database.lookup(names, score)
        )

    def search(self, name: str, score=0.5) -> Iterator[DatabasePlant]:
        """Search for the scientific name by common name in all databases."""
        return self.merge_all(
            plant.with_database(database_name)
            for database_name, database in self.items()
            for plant in database.search(name, score)
        )

    def merge_all(
        self, plants: Iterator[DatabasePlant]
    ) -> Iterator[DatabasePlant]:
        """Group plants by scientific name, merging numbers and strings."""
        keyfunc = attrgetter("scientific_name")
        return (
            self.merge(p)
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

        return DatabasePlant(merge(plants, resolve))
