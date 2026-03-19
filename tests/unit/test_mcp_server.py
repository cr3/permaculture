"""Unit tests for the MCP server module."""

import pytest

from permaculture.database import Database
from permaculture.mcp_server import (
    get_allowed_hosts,
    get_allowed_origins,
    lookup_plants_in,
    search_plants_in,
)
from permaculture.plant import IngestorPlant


def test_get_allowed_hosts_defaults():
    """Allowed hosts should include localhost and 127.0.0.1 by default."""
    result = get_allowed_hosts({})
    assert result == ["localhost:*", "127.0.0.1:*"]


def test_get_allowed_hosts_server_ip():
    """Setting SERVER_IP in the env should allow that host."""
    result = get_allowed_hosts({"SERVER_IP": "1.2.3.4"})
    assert "1.2.3.4:*" in result


def test_get_allowed_hosts_server_hostname():
    """Setting SERVER_HOSTNAME in the env should allow that host."""
    result = get_allowed_hosts({"SERVER_HOSTNAME": "example.com"})
    assert "example.com" in result
    assert "example.com:*" in result


def test_get_allowed_origins_defaults():
    """Allowed origins should include localhost by default."""
    result = get_allowed_origins({})
    assert result == ["http://localhost:*"]


def test_get_allowed_origins_server_hostname():
    """Setting SERVER_HOSTNAME in the env should allow that origin."""
    result = get_allowed_origins({"SERVER_HOSTNAME": "example.com"})
    assert "http://example.com" in result
    assert "http://example.com:*" in result


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
