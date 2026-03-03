"""Unit tests for the ingestor module."""

from unittest.mock import Mock

import pytest

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


def test_ingestors_select_all():
    """Selecting with empty names should return all ingestors."""
    ingestors = Ingestors({"a": 1, "b": 2})
    assert ingestors.select([]) == {"a": 1, "b": 2}


def test_ingestors_select_some():
    """Selecting by name should filter ingestors."""
    ingestors = Ingestors({"a": 1, "b": 2})
    assert ingestors.select(["a"]) == {"a": 1}


def test_ingestors_select_unknown():
    """Selecting unknown names should raise ValueError."""
    ingestors = Ingestors({"a": 1, "b": 2})
    with pytest.raises(ValueError, match="unknown ingestor"):
        ingestors.select(["c"])
