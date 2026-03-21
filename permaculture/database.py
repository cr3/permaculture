"""Database utilities."""

import json
import os
from collections import defaultdict
from collections.abc import Iterator
from itertools import starmap
from operator import mul
from pathlib import Path

from appdirs import user_cache_dir
from attrs import define, field
from yarl import URL

from permaculture.data import merge
from permaculture.plant import DatabasePlant, IngestorPlant
from permaculture.sqlite import connect as sqliteconnect

DEFAULT_DATABASE = str(Path(user_cache_dir("permaculture")) / "permaculture.db")


@define(frozen=True, slots=False)
class Database:
    """Local SQLite database for plant records."""

    conn = field()

    @classmethod
    def from_env(cls, env=os.environ) -> "Database":
        """Create a Database from the environment."""
        url = env.get("PERMACULTURE_DATABASE", DEFAULT_DATABASE)
        return cls.from_url(url)

    @classmethod
    def from_url(cls, url: str | URL) -> "Database":
        """Create a Database from a URL or file path."""
        return cls(sqliteconnect(url))

    def is_initialized(self) -> bool:
        """Return whether the database schema has been created."""
        row = self.conn.execute(
            "SELECT count(*) FROM sqlite_master"
            " WHERE type = 'table' AND name = 'plants'"
        ).fetchone()
        return row[0] > 0

    def initialize(self) -> None:
        """Create tables and indexes."""
        with self.conn as conn:
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
                "CREATE INDEX IF NOT EXISTS idx_sci ON plants(scientific_name)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cn ON common_names(name)")
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS names_fts"
                " USING fts5(name, plant_id UNINDEXED, tokenize='trigram')"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plant_attributes (
                    plant_id    INTEGER NOT NULL REFERENCES plants(id),
                    key         TEXT NOT NULL,
                    value_text  TEXT,
                    value_bool  INTEGER,
                    value_int   INTEGER,
                    value_float REAL
                )
            """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_attr_key_text"
                " ON plant_attributes(key, value_text)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_attr_key_bool"
                " ON plant_attributes(key, value_bool)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_attr_key_int"
                " ON plant_attributes(key, value_int)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_attr_key_float"
                " ON plant_attributes(key, value_float)"
            )

    def delete_ingestor(self, name) -> None:
        """Remove all data for an ingestor."""
        with self.conn as conn:
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
            conn.execute(
                "DELETE FROM plant_attributes WHERE plant_id IN"
                " (SELECT id FROM plants WHERE ingestor = ?)",
                (name,),
            )
            conn.execute("DELETE FROM plants WHERE ingestor = ?", (name,))

    def write_batch(self, records) -> None:
        """Persist a batch of plant records.

        Each record replaces any existing entry for the same
        (ingestor, scientific_name) pair, keeping the database
        free of duplicates even across retries.
        """
        with self.conn as conn:
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
                    "DELETE FROM plant_attributes WHERE plant_id IN"
                    " (SELECT id FROM plants"
                    "  WHERE ingestor = ? AND scientific_name = ?)",
                    (record.ingestor, record.scientific_name),
                )
                conn.execute(
                    "DELETE FROM plants WHERE ingestor = ? AND scientific_name = ?",
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
                    "INSERT INTO common_names (plant_id, name) VALUES (?, ?)",
                    [(pid, n) for n in common_names],
                )
                fts_rows = [
                    (record.scientific_name, pid),
                    *((n, pid) for n in common_names),
                ]
                conn.executemany(
                    "INSERT INTO names_fts (name, plant_id) VALUES (?, ?)",
                    fts_rows,
                )
                attr_rows = []
                attr_type_slot = {
                    bool: lambda v: (None, int(v), None, None),
                    int: lambda v: (None, None, v, None),
                    float: lambda v: (None, None, None, v),
                    str: lambda v: (v, None, None, None),
                }
                for key, value in record.data.items():
                    to_slot = attr_type_slot.get(type(value))
                    if to_slot is not None:
                        attr_rows.append((pid, key, *to_slot(value)))
                conn.executemany(
                    "INSERT INTO plant_attributes"
                    " (plant_id, key, value_text, value_bool, value_int, value_float)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    attr_rows,
                )

    def ingestors(self, include=None) -> list[str]:
        """Return the distinct ingestor names in the database.

        :param include: Optional regex to filter ingestors.
        """
        with self.conn as conn:
            all_ingestors = [
                row[0] for row in conn.execute("SELECT DISTINCT ingestor FROM plants")
            ]

        if include is None:
            return all_ingestors

        return [s for s in all_ingestors if include.match(s)]

    def iterate(self) -> Iterator[DatabasePlant]:
        """Iterate over all plants, merging across sources."""
        return _merge_all(self._iterate_raw())

    def _iterate_raw(self):
        """Yield plants for all rows."""
        with self.conn as conn:
            for ingestor, title, source, data, weight in conn.execute(
                "SELECT ingestor, title, source, data, weight FROM plants"
            ):
                yield IngestorPlant(
                    json.loads(data),
                    weight,
                    ingestor=ingestor,
                    title=title,
                    source=source,
                )

    def lookup(self, names: list[str]) -> Iterator[DatabasePlant]:
        """Lookup characteristics by scientific names, merging across ingestors."""
        if not names:
            return

        with self.conn as conn:
            placeholders = ",".join("?" * len(names))
            rows = conn.execute(
                "SELECT ingestor, title, source, data, weight FROM plants"  # noqa: S608
                f" WHERE scientific_name IN ({placeholders})",
                names,
            )
            yield from _merge_all(
                IngestorPlant(
                    json.loads(data),
                    weight,
                    ingestor=ing,
                    title=title,
                    source=source,
                )
                for ing, title, source, data, weight in rows
            )

    def search(
        self,
        *,
        name: str | None = None,
        filters: dict | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Iterator[DatabasePlant]:
        """Search for plants by name and/or characteristics.

        :param name: Optional fuzzy name search.  Results are ranked
            by FTS5 BM25 relevance (best matches first).
        :param filters: Key-value pairs to filter by.
            Use ``{"key": value}`` for exact matches, or
            ``{"key": {"gt": v, "lte": v}}`` for numeric ranges.
        :param limit: Maximum number of plants to return.
        :param offset: Number of plants to skip.
        """
        if not name and not filters:
            return

        names_query, params = _search_query(name, filters)
        if limit is not None:
            names_query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        query = (
            "SELECT p.ingestor, p.title, p.source, p.data, p.weight"  # noqa: S608
            f" FROM plants p JOIN ({names_query}) AS page"
            " ON p.scientific_name = page.scientific_name"
            " ORDER BY page.best_rank"
        )

        with self.conn as conn:
            rows = conn.execute(query, params)
            yield from _merge_all(
                IngestorPlant(
                    json.loads(data),
                    weight,
                    ingestor=ing,
                    title=title,
                    source=source,
                )
                for ing, title, source, data, weight in rows
            )

    def search_count(
        self,
        *,
        name: str | None = None,
        filters: dict | None = None,
    ) -> int:
        """Count distinct scientific names matching a search.

        Uses the same filtering logic as :meth:`search` but returns
        only the count, without materializing the results.
        """
        if not name and not filters:
            return 0

        names_query, params = _search_query(name, filters)
        with self.conn as conn:
            return conn.execute(
                f"SELECT COUNT(*) FROM ({names_query})", params,  # noqa: S608
            ).fetchone()[0]

    def list_characteristics(self) -> list[dict]:
        """Return distinct characteristic keys with types and counts."""
        with self.conn as conn:
            rows = conn.execute(
                "SELECT key, COUNT(*),"
                " SUM(CASE WHEN value_bool IS NOT NULL THEN 1 ELSE 0 END),"
                " SUM(CASE WHEN value_int IS NOT NULL THEN 1 ELSE 0 END),"
                " MIN(value_int),"
                " MAX(value_int),"
                " SUM(CASE WHEN value_float IS NOT NULL THEN 1 ELSE 0 END),"
                " MIN(value_float),"
                " MAX(value_float)"
                " FROM plant_attributes"
                " GROUP BY key ORDER BY key"
            ).fetchall()
        result = []
        for (
            key, count, bool_count,
            int_count, int_min, int_max,
            float_count, float_min, float_max,
        ) in rows:
            if bool_count > 0:
                result.append(
                    {"key": key, "type": "bool", "count": count}
                )
            elif int_count > 0:
                result.append({
                    "key": key,
                    "type": "int",
                    "count": count,
                    "min": int_min,
                    "max": int_max,
                })
            elif float_count > 0:
                result.append({
                    "key": key,
                    "type": "float",
                    "count": count,
                    "min": float_min,
                    "max": float_max,
                })
            else:
                result.append(
                    {"key": key, "type": "text", "count": count}
                )
        return result


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
        if key != "scientific name":
            sources[key] = [p.ingestor for p in plants if key in p]

    ingestors = {
        p.ingestor: {"title": p.title, "source": p.source} for p in plants if p.ingestor
    }

    def resolve(key, values):
        weights = [p.weight for p in plants if key in p]
        if isinstance(values[0], float | int) and not isinstance(values[0], bool):
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


def _search_query(name, filters):
    """Build a query selecting plants that match."""
    filter_clauses, filter_params = _filter_conditions(filters or {})

    if name:
        query = (
            "SELECT p.scientific_name, MIN(fts.rank) AS best_rank"
            " FROM names_fts fts"
            " JOIN plants p ON fts.plant_id = p.id"
            " WHERE fts.name MATCH ?"
        )
        params = [f'"{name}"']
        for clause in filter_clauses:
            query += f" AND {clause}"
        params.extend(filter_params)
        query += " GROUP BY p.scientific_name ORDER BY best_rank"
    else:
        query = (
            "SELECT DISTINCT p.scientific_name, 0 AS best_rank"
            " FROM plants p"
        )
        params = list(filter_params)
        if filter_clauses:
            query += " WHERE " + " AND ".join(filter_clauses)

    return query, params



_FILTER_OPS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


def _filter_conditions(filters):
    """Build SQL WHERE clauses from a filters dict."""
    conditions = []
    params = []
    for key, value in filters.items():
        if isinstance(value, bool):
            conditions.append(
                "p.id IN (SELECT plant_id FROM plant_attributes"
                " WHERE key = ? AND value_bool = ?)"
            )
            params.extend([key, int(value)])
        elif isinstance(value, dict):
            sub = (
                "p.id IN (SELECT plant_id FROM plant_attributes"
                " WHERE key = ?"
            )
            sub_params = [key]
            for op, v in value.items():
                if op not in _FILTER_OPS:
                    raise ValueError(
                        f"Unknown filter operator: {op!r}"
                    )
                col = "value_int" if isinstance(v, int) else "value_float"
                sub += f" AND COALESCE({col}, value_float, value_int)"
                sub += f" {_FILTER_OPS[op]} ?"
                sub_params.append(v)
            sub += ")"
            conditions.append(sub)
            params.extend(sub_params)
        elif isinstance(value, int):
            conditions.append(
                "p.id IN (SELECT plant_id FROM plant_attributes"
                " WHERE key = ? AND value_int = ?)"
            )
            params.extend([key, value])
        elif isinstance(value, float):
            conditions.append(
                "p.id IN (SELECT plant_id FROM plant_attributes"
                " WHERE key = ? AND value_float = ?)"
            )
            params.extend([key, value])
        else:
            conditions.append(
                "p.id IN (SELECT plant_id FROM plant_attributes"
                " WHERE key = ? AND value_text = ?)"
            )
            params.extend([key, str(value)])
    return conditions, params
