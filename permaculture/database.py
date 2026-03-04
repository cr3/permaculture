"""Database utilities."""

import json
import sqlite3
from collections.abc import Iterator, Mapping
from itertools import groupby, starmap
from operator import attrgetter, mul
from pathlib import Path

from attrs import define, field

from permaculture.data import merge
from permaculture.nlp import Extractor, normalize, score
from permaculture.storage import FileStorage


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
    """Local SQLite database for plant records."""

    db_path: Path = field(converter=Path)

    @classmethod
    def from_storage(cls, storage):
        """Create a Database from a storage provider."""
        if isinstance(storage, FileStorage):
            return cls(storage.base_dir / "permaculture.db")
        return cls(":memory:")

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _extract(self, query, choices):
        return Extractor(query, normalize, score).extract_one(choices)[0]

    def initialize(self):
        """Create tables and indexes."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plants (
                    id INTEGER PRIMARY KEY,
                    source TEXT NOT NULL,
                    scientific_name TEXT NOT NULL,
                    data TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS common_names (
                    plant_id INTEGER REFERENCES plants(id),
                    name TEXT NOT NULL
                )
            """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sci" " ON plants(scientific_name)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cn" " ON common_names(name)")
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS names_fts"
                " USING fts5(name, plant_id UNINDEXED, tokenize='trigram')"
            )

    def write_batch(self, source, records):
        """Persist a batch of plant records."""
        with self._connect() as conn:
            for record in records:
                data_json = json.dumps(record.data)
                cur = conn.execute(
                    "INSERT INTO plants"
                    " (source, scientific_name, data, weight)"
                    " VALUES (?, ?, ?, ?)",
                    (source, record.scientific_name, data_json, record.weight),
                )
                pid = cur.lastrowid
                common_names = record.common_names
                conn.executemany(
                    "INSERT INTO common_names (plant_id, name)" " VALUES (?, ?)",
                    [(pid, n) for n in common_names],
                )
                fts_rows = [
                    (record.scientific_name, pid),
                    *((n, pid) for n in common_names),
                ]
                conn.executemany(
                    "INSERT INTO names_fts (name, plant_id)" " VALUES (?, ?)",
                    fts_rows,
                )

    def sources(self, include=None) -> list[str]:
        """Return the distinct source names in the database.

        :param include: Optional regex to filter sources.
        """
        with self._connect() as conn:
            all_sources = [
                row[0] for row in conn.execute("SELECT DISTINCT source FROM plants")
            ]

        if include is None:
            return all_sources

        return [s for s in all_sources if include.match(s)]

    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over all plants, merging across sources."""
        return _merge_all(
            plant.with_database(source) for source, plant in self._iterate_raw()
        )

    def _iterate_raw(self):
        """Yield (source, plant) pairs for all rows."""
        with self._connect() as conn:
            for source, data, weight in conn.execute(
                "SELECT source, data, weight FROM plants"
            ):
                yield source, DatabasePlant(json.loads(data), weight)

    def lookup(self, names: list[str], score: float) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names, merging across sources."""
        if not names:
            return

        with self._connect() as conn:
            placeholders = ",".join("?" * len(names))
            rows = conn.execute(
                "SELECT source, data, weight FROM plants"  # noqa: S608
                f" WHERE scientific_name IN ({placeholders})",
                names,
            )
            yield from _merge_all(
                DatabasePlant(json.loads(data), weight).with_database(src)
                for src, data, weight in rows
            )

    def search(self, name: str, score: float) -> Iterator[DatabasePlant]:
        """Search for plants by name using FTS5 trigram matching."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT p.source, p.data, p.weight"
                " FROM names_fts fts"
                " JOIN plants p ON fts.plant_id = p.id"
                " WHERE fts.name MATCH ?",
                (f'"{name}"',),
            )
            yield from _merge_all(
                plant.with_database(src)
                for src, data, weight in rows
                if self._extract(
                    name,
                    (plant := DatabasePlant(json.loads(data), weight)).names,
                )
                >= score
            )


def _merge_all(
    plants: Iterator[DatabasePlant],
) -> Iterator[DatabasePlant]:
    """Group plants by scientific name, merging numbers and strings."""
    keyfunc = attrgetter("scientific_name")
    return (_merge(p) for _, p in groupby(sorted(plants, key=keyfunc), keyfunc))


def _merge(plants: Iterator[DatabasePlant]) -> DatabasePlant:
    """Merge plants with the same scientific name using weighted resolution."""
    plants = list(plants)

    def resolve(key, values):
        weights = [p.weight for p in plants if key in p]
        if isinstance(values[0], float | int):
            value = sum(starmap(mul, zip(weights, values, strict=True))) / sum(weights)
        else:
            _, value = max(zip(weights, values, strict=True))

        return value

    weights = [p.weight for p in plants]
    avg_weight = sum(weights) / len(weights) if weights else 1.0
    return DatabasePlant(merge(plants, resolve), avg_weight)
