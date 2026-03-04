"""Unit tests for the database module."""

from unittest.mock import Mock

import pytest

from permaculture.database import (
    Database,
    DatabaseNotFoundError,
    DatabasePlant,
    _merge,
    _merge_all,
)


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary SQLite database with test data."""
    path = tmp_path / "permaculture.db"
    database = Database(path)
    database.initialize()
    return path


def test_database_plant_with_database(unique):
    plant = unique("plant")
    assert "database" not in plant
    plant = plant.with_database("a")
    assert plant["database/a"]


def test_database_load_empty(tmp_path):
    """Loading should raise when no database exists."""
    storage = Mock(base_dir=tmp_path)
    config = Mock(databases=[], storage=storage)
    with pytest.raises(DatabaseNotFoundError):
        Database.load(config)


def test_database_load(db_path):
    """Loading should return a Database when the file exists."""
    storage = Mock(base_dir=db_path.parent)
    config = Mock(databases=[], storage=storage)
    database = Database.load(config)
    assert database is not None
    assert database.db_path == db_path


def test_database_sources(db_path):
    """Sources should list distinct source names."""
    database = Database(db_path)
    database.write_batch("a", [DatabasePlant({"scientific name": "x"})])
    database.write_batch("b", [DatabasePlant({"scientific name": "y"})])

    assert sorted(database.sources()) == ["a", "b"]


def test_database_sources_filtered(db_path):
    """Sources should filter by regex when provided."""
    database = Database(db_path)
    database.write_batch("a", [DatabasePlant({"scientific name": "x"})])
    database.write_batch("b", [DatabasePlant({"scientific name": "y"})])

    import re

    include = re.compile("a", re.I)
    assert database.sources(include) == ["a"]


def test_database_iterate(db_path):
    """Iterating should return all plants from the local database."""
    database = Database(db_path)
    database.write_batch("a", [DatabasePlant({"scientific name": "x"})])

    database = Database(db_path)
    result = list(database.iterate())
    assert len(result) == 1
    assert result[0]["scientific name"] == "x"


def test_database_lookup(db_path):
    """Lookup should return plants matching scientific names."""
    database = Database(db_path)
    database.write_batch(
        "a",
        [
            DatabasePlant({"scientific name": "symphytum officinale"}),
            DatabasePlant({"scientific name": "achillea millefolium"}),
        ],
    )

    database = Database(db_path)
    result = list(database.lookup(["symphytum officinale"], 1.0))
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_database_search(db_path):
    """Search should return plants matching common name."""
    database = Database(db_path)
    database.write_batch(
        "a",
        [
            DatabasePlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                }
            ),
        ],
    )

    database = Database(db_path)
    result = list(database.search("comfrey", 0.5))
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_database_search_by_scientific_name(db_path):
    """Search should also match on scientific name via FTS5."""
    database = Database(db_path)
    database.write_batch(
        "a",
        [
            DatabasePlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                }
            ),
        ],
    )

    result = list(database.search("symphytum", 0.5))
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_database_iterate_merges_sources(db_path):
    """Iterating should merge plants from multiple sources."""
    database = Database(db_path)
    database.write_batch("a", [DatabasePlant({"scientific name": "x"})])
    database.write_batch("b", [DatabasePlant({"scientific name": "y"})])

    result = list(database.iterate())
    assert len(result) == 2
    names = {p.scientific_name for p in result}
    assert names == {"x", "y"}


def test_database_iterate_tags_source(db_path):
    """Iterating should tag each plant with its source."""
    database = Database(db_path)
    database.write_batch("pfaf", [DatabasePlant({"scientific name": "x"})])

    result = list(database.iterate())
    assert result[0]["database/pfaf"]


@pytest.mark.parametrize(
    "plants, expected",
    [
        pytest.param(
            [],
            [],
            id="empty",
        ),
        pytest.param(
            [DatabasePlant({"scientific name": "a"})],
            [DatabasePlant({"scientific name": "a"})],
            id="single",
        ),
        pytest.param(
            [
                DatabasePlant({"scientific name": "a"}),
                DatabasePlant({"scientific name": "a"}),
            ],
            [DatabasePlant({"scientific name": "a"})],
            id="group by scientific name",
        ),
    ],
)
def test_database_merge_all(plants, expected):
    """Merging all plants should group by scientific name."""
    result = list(_merge_all(plants))
    assert result == expected


@pytest.mark.parametrize(
    "plants, expected",
    [
        pytest.param(
            [],
            DatabasePlant(),
            id="empty",
        ),
        pytest.param(
            [DatabasePlant({"scientific name": "a"})],
            DatabasePlant({"scientific name": "a"}),
            id="single",
        ),
        pytest.param(
            [
                DatabasePlant({"scientific name": "a"}),
                DatabasePlant({"scientific name": "a"}),
            ],
            DatabasePlant({"scientific name": "a"}),
            id="group by scientific name",
        ),
        pytest.param(
            [
                DatabasePlant({"scientific name": "a", "x": 1}, 2.0),
                DatabasePlant({"scientific name": "a", "x": 4}, 1.0),
            ],
            DatabasePlant({"scientific name": "a", "x": 2.0}, 1.5),
            id="merge numbers",
        ),
        pytest.param(
            [
                DatabasePlant({"scientific name": "a", "x": "b"}, 2.0),
                DatabasePlant({"scientific name": "a", "x": "c"}, 1.0),
            ],
            DatabasePlant({"scientific name": "a", "x": "b"}, 1.5),
            id="merge strings",
        ),
    ],
)
def test_database_merge(plants, expected):
    """Merging plants should merge numbers and strings."""
    result = _merge(plants)
    assert result == expected


def test_database_initialize_idempotent(db_path):
    """Initializing twice should be idempotent."""
    database = Database(db_path)
    database.initialize()


def test_database_write_batch_and_iterate(db_path):
    """Writing a batch should persist records retrievable via iterate."""
    database = Database(db_path)
    records = [
        DatabasePlant(
            {
                "scientific name": "symphytum officinale",
                "common name/comfrey": True,
            }
        ),
        DatabasePlant(
            {
                "scientific name": "achillea millefolium",
                "common name/yarrow": True,
            }
        ),
    ]
    database.write_batch("pfaf", records)
    result = list(database.iterate())
    assert len(result) == 2
    names = {p["scientific name"] for p in result}
    assert names == {"symphytum officinale", "achillea millefolium"}


def test_database_search_no_match(db_path):
    """Searching for a non-existent name should return empty."""
    database = Database(db_path)
    database.write_batch(
        "pfaf",
        [
            DatabasePlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                }
            ),
        ],
    )
    result = list(database.search("nonexistent", 0.5))
    assert result == []


def test_database_lookup_empty(db_path):
    """Lookup with empty names should return empty."""
    database = Database(db_path)
    result = list(database.lookup([], 1.0))
    assert result == []


def test_database_weight_preserved(db_path):
    """Weight should be preserved through write and read."""
    database = Database(db_path)
    database.write_batch(
        "pfaf",
        [
            DatabasePlant({"scientific name": "test"}, weight=2.5),
        ],
    )
    result = list(database.iterate())
    assert result[0].weight == 2.5
