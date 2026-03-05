"""Unit tests for the database module."""

from unittest.mock import Mock

import pytest

from permaculture.database import (
    Database,
    DatabasePlant,
    Databases,
)
from permaculture.sink import SQLiteSink


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary SQLite database with test data."""
    path = tmp_path / "permaculture.db"
    sink = SQLiteSink(path)
    sink.initialize()
    return path


def test_database_plant_with_database(unique):
    plant = unique("plant")
    assert "database" not in plant
    plant = plant.with_database("a")
    assert plant["database/a"]


def test_database_load_empty(tmp_path):
    """Loading should return empty when no database exists."""
    storage = Mock(base_dir=tmp_path)
    config = Mock(databases=[], storage=storage)
    databases = Databases.load(config)
    assert len(databases) == 0


def test_database_load_all(db_path):
    """Loading should instantiate all databases by default."""
    sink = SQLiteSink(db_path)
    sink.write_batch("a", [DatabasePlant({"scientific name": "x"})])
    sink.write_batch("b", [DatabasePlant({"scientific name": "y"})])

    storage = Mock(base_dir=db_path.parent)
    config = Mock(databases=[], storage=storage)
    databases = Databases.load(config)
    assert "a" in databases
    assert "b" in databases


def test_database_load_one(db_path):
    """Loading can filter databases from the config."""
    sink = SQLiteSink(db_path)
    sink.write_batch("a", [DatabasePlant({"scientific name": "x"})])
    sink.write_batch("b", [DatabasePlant({"scientific name": "y"})])

    storage = Mock(base_dir=db_path.parent)
    config = Mock(databases=["a"], storage=storage)
    databases = Databases.load(config)
    assert "a" in databases
    assert "b" not in databases


def test_database_iterate(db_path):
    """Iterating should return all plants from the local database."""
    sink = SQLiteSink(db_path)
    sink.write_batch("a", [DatabasePlant({"scientific name": "x"})])

    database = Database(db_path)
    result = list(database.iterate())
    assert len(result) == 1
    assert result[0]["scientific name"] == "x"


def test_database_lookup(db_path):
    """Lookup should return plants matching scientific names."""
    sink = SQLiteSink(db_path)
    sink.write_batch(
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
    sink = SQLiteSink(db_path)
    sink.write_batch(
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


def test_databases_iterate(unique):
    """Iterating should iterate over all databases."""
    a, b = unique("plant"), unique("plant")
    databases = Databases(
        {
            "a": Mock(iterate=Mock(return_value=[a])),
            "b": Mock(iterate=Mock(return_value=[b])),
        },
    )
    result = list(databases.iterate())
    assert result == [a, b]
    assert a["database/a"]
    assert b["database/b"]


def test_databases_lookup(unique):
    """Looking up should iterate over all databases."""
    a, b = unique("plant"), unique("plant")
    databases = Databases(
        {
            "a": Mock(lookup=Mock(return_value=[a])),
            "b": Mock(lookup=Mock(return_value=[b])),
        },
    )
    result = list(databases.lookup(None))
    assert result == [a, b]
    assert a["database/a"]
    assert b["database/b"]


def test_databases_search(unique):
    """Searching should iterate over all databases."""
    a, b = unique("plant"), unique("plant")
    databases = Databases(
        {
            "a": Mock(search=Mock(return_value=[a])),
            "b": Mock(search=Mock(return_value=[b])),
        },
    )
    result = list(databases.search(None))
    assert result == [a, b]


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
    result = list(Databases({}).merge_all(plants))
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
            DatabasePlant({"scientific name": "a", "x": 2.0}),
            id="merge numbers",
        ),
        pytest.param(
            [
                DatabasePlant({"scientific name": "a", "x": "b"}, 2.0),
                DatabasePlant({"scientific name": "a", "x": "c"}, 1.0),
            ],
            DatabasePlant({"scientific name": "a", "x": "b"}),
            id="merge strings",
        ),
    ],
)
def test_database_merge(plants, expected):
    """Merging plants should merge numbers and strings."""
    result = Databases({}).merge(plants)
    assert result == expected
