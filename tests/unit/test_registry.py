"""Unit tests for the registry module."""
from importlib.metadata import EntryPoint
from unittest.mock import patch

import pytest

import permaculture.registry
from permaculture.registry import (
    registry_add,
    registry_get,
    registry_load,
    registry_remove,
)


def test_registry_load():
    """Entry points should be loaded into a registry dictionary."""
    with patch.object(
        permaculture.registry,
        "get_entry_points",
    ) as mock_entry_points:
        mock_entry_points.return_value = iter(
            [
                EntryPoint("registry", "permaculture.registry", "permaculture.group"),
            ]
        )
        registry = registry_load("group")
        assert "registry" in registry["group"]
        assert registry["group"]["registry"] == permaculture.registry


def test_registry_load_ignore():
    """Entry points that fail to load should be ignored."""
    with patch.object(
        permaculture.registry,
        "get_entry_points",
    ) as mock_entry_points:
        mock_entry_points.return_value = iter(
            [
                EntryPoint("error", "permaculture.registry", "permaculture.group"),
            ]
        )
        registry = registry_load("group")
        assert "test" not in registry


def test_registry_add():
    """Adding an entry in an empty registry should return a new registry."""
    registry = registry_add("group", "name", True)
    assert registry["group"]["name"]


def test_registry_add_existing():
    """Adding an entry in an existing registry should replace existing."""
    registry = {
        "group": {
            "name": False,
        },
    }
    registry = registry_add("group", "name", True, registry)
    assert registry["group"]["name"]


def test_registry_remove_existing():
    """Removing an existing entry from a registry should remove it."""
    registry = registry_add("group", "name1", True)
    registry = registry_add("group", "name2", True)
    registry_remove("group", "name1", registry)
    assert "name1" not in registry["group"]
    assert "name2" in registry["group"]


def test_registry_remove_non_existing():
    """Removing an existing entry from a registry should return silently."""
    registry = registry_add("group", "name2", True)
    registry_remove("group", "name1", registry)
    assert "name2" in registry["group"]


def test_registry_get():
    """Getting an existing entry from a registry should find it."""
    registry = registry_add("group", "name", True)
    assert registry_get("group", "name", registry)


def test_registry_get_error():
    """Getting a non-existing entry from a registry should raise."""
    with pytest.raises(KeyError):
        registry_get("group", "name", {})


@pytest.mark.parametrize(
    "group,name",
    [
        ("serializers", "application/json"),
        ("serializers", "text/plain"),
    ],
)
def test_registry_get_setup(group, name):
    """Getting from the registry should lookup entry points in setup.py."""
    registry_get(group, name)
