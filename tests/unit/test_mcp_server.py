"""Unit tests for the MCP server module."""

import pytest

from permaculture.database import Database
from permaculture.mcp_server import lookup_plants_in, search_plants_in
from permaculture.plant import IngestorPlant


@pytest.fixture
def database():
    """Create a populated in-memory database for MCP server testing."""
    db = Database.from_url(":memory:")
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
    result = search_plants_in(database, "comfrey")

    assert len(result) == 1
    assert result[0]["scientific_name"] == "symphytum officinale"
    assert "comfrey" in result[0]["common_names"]


def test_search_plants_no_match(database):
    """Searching for a non-existent name should return empty."""
    result = search_plants_in(database, "nonexistent")

    assert result == []


def test_lookup_plants(database):
    """Looking up by scientific name should return matching plants."""
    result = lookup_plants_in(database, ["symphytum officinale"])

    assert len(result) == 1
    assert result[0]["scientific_name"] == "symphytum officinale"
    assert result[0]["ingestors"] == {
        "pfaf": {"title": "Plants For A Future", "source": "https://pfaf.org/"},
    }


def test_lookup_plants_empty(database):
    """Looking up with empty names should return empty."""
    result = lookup_plants_in(database, [])

    assert result == []
