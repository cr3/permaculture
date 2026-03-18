"""Database utilities."""

import json
import os
import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from itertools import starmap
from operator import mul
from pathlib import Path

from attrs import define, field

from permaculture.data import merge
from permaculture.nlp import Extractor, normalize, score
from permaculture.plant import DatabasePlant, IngestorPlant
from permaculture.storage import Storage


@define(frozen=True)
class Database:
    """Local SQLite database for plant records."""

    db_path: Path = field(converter=Path)

    @classmethod
    def from_env(cls, env=os.environ):
        """Get a Database from the environment."""
        storage = Storage.from_env(env)
        return cls.from_storage(storage)

    @classmethod
    def from_storage(cls, storage):
        """Create a Database from a storage provider."""
        try:
            return cls(storage.base_dir / "permaculture.db")
        except AttributeError:
            return cls(":memory:")

    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
                    ingestor TEXT NOT NULL,
                    title TEXT NOT NULL,
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
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_ingestor_sci"
                " ON plants(ingestor, scientific_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sci" " ON plants(scientific_name)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cn" " ON common_names(name)")
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS names_fts"
                " USING fts5(name, plant_id UNINDEXED, tokenize='trigram')"
            )

    def delete_ingestor(self, name):
        """Remove all data for an ingestor."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM names_fts WHERE plant_id IN"
                " (SELECT id FROM plants WHERE ingestor = ?)",
                (name,),
            )
            conn.execute(
                "DELETE FROM common_names WHERE plant_id IN"
                " (SELECT id FROM plants WHERE ingestor = ?)",
                (name,),
            )
            conn.execute("DELETE FROM plants WHERE ingestor = ?", (name,))

    def write_batch(self, records):
        """Persist a batch of plant records.

        Each record replaces any existing entry for the same
        (ingestor, scientific_name) pair, keeping the database
        free of duplicates even across retries.
        """
        with self._connect() as conn:
            for record in records:
                # Remove stale row (if any) before inserting.
                conn.execute(
                    "DELETE FROM names_fts WHERE plant_id IN"
                    " (SELECT id FROM plants"
                    "  WHERE ingestor = ? AND scientific_name = ?)",
                    (record.ingestor, record.scientific_name),
                )
                conn.execute(
                    "DELETE FROM common_names WHERE plant_id IN"
                    " (SELECT id FROM plants"
                    "  WHERE ingestor = ? AND scientific_name = ?)",
                    (record.ingestor, record.scientific_name),
                )
                conn.execute(
                    "DELETE FROM plants"
                    " WHERE ingestor = ? AND scientific_name = ?",
                    (record.ingestor, record.scientific_name),
                )

                data_json = json.dumps(record.data)
                cur = conn.execute(
                    "INSERT INTO plants"
                    " (ingestor, title, source, scientific_name, data, weight)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        record.ingestor,
                        record.title,
                        record.source,
                        record.scientific_name,
                        data_json,
                        record.weight,
                    ),
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

    def ingestors(self, include=None) -> list[str]:
        """Return the distinct ingestor names in the database.

        :param include: Optional regex to filter ingestors.
        """
        with self._connect() as conn:
            all_ingestors = [
                row[0]
                for row in conn.execute("SELECT DISTINCT ingestor FROM plants")
            ]

        if include is None:
            return all_ingestors

        return [s for s in all_ingestors if include.match(s)]

    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over all plants, merging across sources."""
        return _merge_all(self._iterate_raw())

    def _iterate_raw(self):
        """Yield plants for all rows."""
        with self._connect() as conn:
            for ingestor, title, source, data, weight in conn.execute(
                "SELECT ingestor, title, source, data, weight FROM plants"
            ):
                yield IngestorPlant(
                    json.loads(data), weight,
                    ingestor=ingestor, title=title, source=source,
                )

    def lookup(self, names: list[str], score: float) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names, merging across ingestors."""
        if not names:
            return

        with self._connect() as conn:
            placeholders = ",".join("?" * len(names))
            rows = conn.execute(
                "SELECT ingestor, title, source, data, weight FROM plants"  # noqa: S608
                f" WHERE scientific_name IN ({placeholders})",
                names,
            )
            yield from _merge_all(
                IngestorPlant(
                    json.loads(data), weight,
                    ingestor=ing, title=title, source=source,
                )
                for ing, title, source, data, weight in rows
            )

    def search(self, name: str, score: float) -> Iterator[DatabasePlant]:
        """Search for plants by name using FTS5 trigram matching."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT p.ingestor, p.title, p.source, p.data, p.weight"
                " FROM names_fts fts"
                " JOIN plants p ON fts.plant_id = p.id"
                " WHERE fts.name MATCH ?",
                (f'"{name}"',),
            )
            yield from _merge_all(
                plant
                for ing, ing_title, source, data, weight in rows
                if self._extract(
                    name,
                    (
                        plant := IngestorPlant(
                            json.loads(data), weight,
                            ingestor=ing, title=ing_title, source=source,
                        )
                    ).names,
                )
                >= score
            )


def _merge_all(
    plants: Iterator[IngestorPlant],
) -> Iterator[DatabasePlant]:
    """Group plants by scientific name, merging numbers and strings."""
    grouped = defaultdict(list)
    for plant in plants:
        grouped[plant.scientific_name].append(plant)
    return (_merge(g) for g in grouped.values())


def _merge(plants: Iterator[IngestorPlant]) -> DatabasePlant:
    """Merge plants with the same scientific name using weighted resolution."""
    plants = list(plants)

    sources = {}
    for key in {k for p in plants for k in p}:
        sources[key] = [p.ingestor for p in plants if key in p]

    ingestors = {
        p.ingestor: {"title": p.title, "source": p.source}
        for p in plants
        if p.ingestor
    }

    def resolve(key, values):
        weights = [p.weight for p in plants if key in p]
        if isinstance(values[0], float | int):
            value = sum(starmap(mul, zip(weights, values, strict=True))) / sum(weights)
        else:
            _, value = max(zip(weights, values, strict=True))

        return value

    weights = [p.weight for p in plants]
    avg_weight = sum(weights) / len(weights) if weights else 1.0
    return DatabasePlant(
        merge(plants, resolve),
        avg_weight,
        ingestors=ingestors,
        sources=sources,
    )
