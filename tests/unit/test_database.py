"""Unit tests for the database module."""

from unittest.mock import Mock

from permaculture.database import Database


def test_database_plant_with_database(unique):
    plant = unique("plant")
    assert "database" not in plant
    plant = plant.with_database("a")
    assert plant["database"] == "a"


def test_database_load_all():
    """Loading should instantiate all databases by default."""
    config = Mock(database=None)
    registry = {
        "databases": {
            "a": Mock(),
            "b": Mock(),
        },
    }
    database = Database.load(config, registry)
    assert "a" in database.databases
    assert "b" in database.databases


def test_database_load_one():
    """Loading can instantiate a single database from the config."""
    config = Mock(database="A")
    registry = {
        "databases": {
            "a": Mock(),
            "b": Mock(),
        },
    }
    database = Database.load(config, registry)
    assert "a" in database.databases
    assert "b" not in database.databases


def test_database_lookup(unique):
    """Looking up should iterate over all databases in the registry."""
    a, b = unique("plant"), unique("plant")
    database = Database(
        databases={
            "a": Mock(lookup=Mock(return_value=[a])),
            "b": Mock(lookup=Mock(return_value=[b])),
        },
    )
    result = list(database.lookup(None))
    assert result == [a, b]
    assert a["database"] == "a"
    assert b["database"] == "b"


def test_database_search(unique):
    """Searching should iterate over all databases in the registry."""
    a, b = unique("plant"), unique("plant")
    database = Database(
        databases={
            "a": Mock(search=Mock(return_value=[a])),
            "b": Mock(search=Mock(return_value=[b])),
        },
    )
    result = list(database.search(None))
    assert result == [a, b]
