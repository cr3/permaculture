"""Unit tests for the API module."""

import pytest
from fastapi.testclient import TestClient

from permaculture.api import app, get_database, group_characteristics
from permaculture.database import Database
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
                    "sun/partial": True,
                    "sun/full": True,
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


@pytest.fixture
def client(database):
    """Create a test client with the database injected."""
    app.dependency_overrides[get_database] = lambda: database
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_plants_search(client):
    """Searching should return matching plants."""
    r = client.get("/permaculture/plants", params={"q": "comfrey"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["scientific_name"] == "symphytum officinale"
    assert "comfrey" in data[0]["common_names"]


def test_get_plants_no_match(client):
    """Searching for a non-existent name should return empty."""
    r = client.get("/permaculture/plants", params={"q": "nonexistent"})
    assert r.status_code == 200
    assert r.json() == []


def test_get_plants_limit(client):
    """Limit should cap the number of results."""
    r = client.get("/permaculture/plants", params={"q": "a", "limit": 1})
    assert r.status_code == 200
    assert len(r.json()) <= 1


def test_get_plant_detail(client):
    """Looking up a plant should return grouped characteristics."""
    r = client.get("/permaculture/plants/symphytum officinale")
    assert r.status_code == 200
    data = r.json()
    assert "scientific name" in data


def test_get_plant_not_found(client):
    """Looking up a missing plant should return empty object."""
    r = client.get("/permaculture/plants/nonexistent species")
    assert r.status_code == 200
    assert r.json() == {}


def test_index_html(client):
    """The index page should return HTML."""
    r = client.get("/permaculture/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Permaculture" in r.text


def test_group_characteristics_boolean_lists():
    """Sub-keys with all True values should become sorted lists."""
    data = {"sun/partial": True, "sun/full": True}
    result = group_characteristics(data)
    assert result == {"sun": ["full", "partial"]}


def test_group_characteristics_mixed():
    """Non-boolean sub-keys should remain as dicts."""
    data = {"bloom/min": "spring", "bloom/max": "summer"}
    result = group_characteristics(data)
    assert result == {"bloom": {"min": "spring", "max": "summer"}}
