"""Unit tests for the MCP server module."""

import pytest
from hamcrest import assert_that, contains_exactly, has_entry, has_items

from permaculture.database import Database
from permaculture.mcp_server import (
    get_allowed_hosts,
    get_allowed_origins,
    list_characteristics_in,
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
                    "sun/full": True,
                    "height": 1.2,
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
                    "sun/full": True,
                    "height": 0.6,
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

    assert result["total_count"] == 1
    assert result["results"][0]["scientific_name"] == "symphytum officinale"
    assert "comfrey" in result["results"][0]["common_names"]


def test_search_plants_no_match(database):
    """Searching for a non-existent name should return empty."""
    result = search_plants_in(database, "nonexistent")

    assert result == {"total_count": 0, "results": []}


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


def test_search_plants_with_filters(database):
    """Searching with filters should return matching plants."""
    result = search_plants_in(
        database, filters={"height": {"gt": 1.0}},
    )

    assert result["total_count"] == 1
    assert_that(result["results"], contains_exactly(
        has_entry("scientific_name", "symphytum officinale"),
    ))


def test_search_plants_with_name_and_filters(database):
    """Combining name and filters should intersect results."""
    result = search_plants_in(
        database, "comfrey", filters={"sun/full": True},
    )

    assert result["total_count"] == 1
    assert_that(result["results"], contains_exactly(
        has_entry("scientific_name", "symphytum officinale"),
    ))


def test_search_plants_filters_no_match(database):
    """Filtering with no matches should return empty."""
    result = search_plants_in(
        database, filters={"sun/full": False},
    )

    assert result == {"total_count": 0, "results": []}


def test_search_plants_unknown_filter_keys(database):
    """Unknown filter keys should return an error with a hint."""
    result = search_plants_in(
        database, filters={"zone_rusticite": 5, "hauteur_m": {"gt": 1}},
    )

    assert "error" in result
    assert "zone_rusticite" in result["error"]
    assert "hauteur_m" in result["error"]
    assert "hint" in result
    assert "list_plant_characteristics" in result["hint"]


def test_search_plants_limit(database):
    """Limiting results should return at most limit items."""
    result = search_plants_in(
        database, filters={"sun/full": True}, limit=1,
    )

    assert result["total_count"] == 2
    assert len(result["results"]) == 1


def test_search_plants_offset(database):
    """Offset should skip the first results."""
    result = search_plants_in(
        database, filters={"sun/full": True}, offset=1,
    )

    assert result["total_count"] == 2
    assert len(result["results"]) == 1


def test_search_plants_multi_ingestor():
    """A plant from two ingestors should appear once in search results."""
    db = Database.from_url(":memory:")
    db.initialize()
    db.write_batch(
        [
            IngestorPlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                    "height": 1.0,
                },
                1.0,
                ingestor="pfaf",
                title="PFAF",
                source="https://pfaf.org/",
            ),
        ],
    )
    db.write_batch(
        [
            IngestorPlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                    "height": 1.4,
                },
                1.0,
                ingestor="usda",
                title="USDA",
                source="https://usda.gov/",
            ),
        ],
    )

    result = search_plants_in(db, "comfrey")

    assert result["total_count"] == 1
    assert_that(result["results"], contains_exactly(
        has_entry("scientific_name", "symphytum officinale"),
    ))


def test_list_plant_characteristics(database):
    """Listing characteristics should return available keys."""
    result = list_characteristics_in(database)
    keys = {c["key"] for c in result}

    assert_that(keys, has_items("height", "sun/full"))
