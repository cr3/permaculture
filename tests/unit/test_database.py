"""Unit tests for the database module."""

from unittest.mock import Mock

from permaculture.database import Database


def test_database_iterate():
    """Iterating should iterate over all databases in the registry."""
    database = Database(
        None,
        databases={
            "a": Mock(iterate=Mock(return_value=[1])),
            "b": Mock(iterate=Mock(return_value=[2])),
        },
    )
    result = list(database.iterate())
    assert result == [1, 2]
