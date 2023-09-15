"""Unit tests for the database module."""

from unittest.mock import Mock

from permaculture.database import Database


def test_database_search():
    """Searching should iterate over all databases in the registry."""
    database = Database(
        None,
        databases={
            "a": Mock(search=Mock(return_value=[1])),
            "b": Mock(search=Mock(return_value=[2])),
        },
    )
    result = list(database.search(None))
    assert result == [1, 2]
