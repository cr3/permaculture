"""Unit tests for the ingestor module."""

from unittest.mock import Mock

from permaculture.ingestor import Ingestors


def test_ingestors_load_all():
    """Loading should instantiate all ingestors by default."""
    config = Mock(databases=[])
    registry = {
        "ingestors": {
            "a": Mock(),
            "b": Mock(),
        },
    }
    ingestors = Ingestors.load(config, registry)
    assert "a" in ingestors
    assert "b" in ingestors


def test_ingestors_load_one():
    """Loading can filter ingestors from the config."""
    config = Mock(databases=["A"])
    registry = {
        "ingestors": {
            "a": Mock(),
            "b": Mock(),
        },
    }
    ingestors = Ingestors.load(config, registry)
    assert "a" in ingestors
    assert "b" not in ingestors
