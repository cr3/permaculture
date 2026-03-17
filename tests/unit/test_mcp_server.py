"""Unit tests for the MCP server module."""

from unittest.mock import patch

import pytest

from permaculture.database import Database
from permaculture.mcp_server import lookup_plants, search_plants
from permaculture.plant import IngestorPlant


@pytest.fixture
def database(tmp_path):
    """Create a populated database backed by a temporary file."""
    db = Database(tmp_path / "permaculture.db")
    db.initialize()
    db.write_batch(
        [
            IngestorPlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                },
                1.0,
                ingestor="pfaf",
                title="Plants For A Future",
                source="https://pfaf.org/",
            ),
            IngestorPlant(
                {
                    "scientific name": "achillea millefolium",
                    "common name/yarrow": True,
                },
                1.0,
                ingestor="pfaf",
                title="Plants For A Future",
                source="https://pfaf.org/",
            ),
        ]
    )
    return db


def test_search_plants(database):
    """Searching by common name should return matching plants."""
    with patch("permaculture.mcp_server._load_database", return_value=database):
        result = search_plants("comfrey")

    assert len(result) == 1
    assert result[0]["scientific_name"] == "symphytum officinale"
    assert "comfrey" in result[0]["common_names"]


def test_search_plants_no_match(database):
    """Searching for a non-existent name should return empty."""
    with patch("permaculture.mcp_server._load_database", return_value=database):
        result = search_plants("nonexistent")

    assert result == []


def test_lookup_plants(database):
    """Looking up by scientific name should return matching plants."""
    with patch("permaculture.mcp_server._load_database", return_value=database):
        result = lookup_plants(["symphytum officinale"])

    assert len(result) == 1
    assert result[0]["scientific_name"] == "symphytum officinale"
    assert result[0]["ingestors"] == {
        "pfaf": {"title": "Plants For A Future", "source": "https://pfaf.org/"},
    }


def test_lookup_plants_empty(database):
    """Looking up with empty names should return empty."""
    with patch("permaculture.mcp_server._load_database", return_value=database):
        result = lookup_plants([])

    assert result == []



