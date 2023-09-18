"""Unit tests for the database module."""

from unittest.mock import Mock

from permaculture.database import Database


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


def test_database_lookup():
    """Looking up should iterate over all databases in the registry."""
    database = Database(
        databases={
            "a": Mock(lookup=Mock(return_value=[1])),
            "b": Mock(lookup=Mock(return_value=[2])),
        },
    )
    result = list(database.lookup(None))
    assert result == [1, 2]


def test_database_search():
    """Searching should iterate over all databases in the registry."""
    database = Database(
        databases={
            "a": Mock(search=Mock(return_value=[1])),
            "b": Mock(search=Mock(return_value=[2])),
        },
    )
    result = list(database.search(None))
    assert result == [1, 2]
