"""Sink protocol and implementations for persisting ingested plant data."""

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from attrs import define, field

from permaculture.database import DatabasePlant


@runtime_checkable
class Sink(Protocol):
    """Protocol for writing batches of plant records to storage."""

    def initialize(self) -> None:
        """Create tables and indexes if needed."""
        ...

    def write_batch(
        self, source: str, records: Iterable[DatabasePlant]
    ) -> None:
        """Persist a batch of plant records from a named source."""
        ...

    def read_all(self) -> list[DatabasePlant]:
        """Read all stored plants."""
        ...

    def search(self, name: str) -> list[DatabasePlant]:
        """Search for plants by common name substring."""
        ...

    def lookup(self, names: list[str]) -> list[DatabasePlant]:
        """Lookup plants by exact scientific names."""
        ...


@define(frozen=True)
class SQLiteSink:
    """SQLite implementation of the Sink protocol."""

    db_path: Path = field(converter=Path)

    def _connect(self):
        return sqlite3.connect(self.db_path)

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
                "CREATE INDEX IF NOT EXISTS idx_sci"
                " ON plants(scientific_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cn" " ON common_names(name)"
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
                conn.executemany(
                    "INSERT INTO common_names (plant_id, name)"
                    " VALUES (?, ?)",
                    [(pid, n) for n in record.common_names],
                )

    def read_all(self):
        """Read all stored plants."""
        with self._connect() as conn:
            rows = conn.execute("SELECT data, weight FROM plants")
            return [
                DatabasePlant(json.loads(data), weight)
                for data, weight in rows
            ]

    def search(self, name):
        """Search for plants by common name substring."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT p.data, p.weight"
                " FROM common_names cn"
                " JOIN plants p ON cn.plant_id = p.id"
                " WHERE cn.name LIKE ?",
                (f"%{name}%",),
            )
            return [
                DatabasePlant(json.loads(data), weight)
                for data, weight in rows
            ]

    def lookup(self, names):
        """Lookup plants by exact scientific names."""
        if not names:
            return []

        with self._connect() as conn:
            placeholders = ",".join("?" * len(names))
            rows = conn.execute(
                "SELECT data, weight FROM plants"  # noqa: S608
                f" WHERE scientific_name IN ({placeholders})",
                names,
            )
            return [
                DatabasePlant(json.loads(data), weight)
                for data, weight in rows
            ]
