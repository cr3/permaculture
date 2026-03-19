"""Unit tests for the API module."""

import pytest
from fastapi.testclient import TestClient

from permaculture.api import (
    app,
    get_database,
    group_characteristics,
    translate_data,
)
from permaculture.database import Database
from permaculture.locales import Locales
from permaculture.plant import IngestorPlant


@pytest.fixture
def database():
    """Create a populated in-memory database for API testing."""
    db = Database.from_url(":memory:")
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
    assert data[0]["scientific name"] == "symphytum officinale"
    assert "comfrey" in data[0]["common names"]


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
    assert data["ingestors"] == {
        "pfaf": {"title": "Plants For A Future", "source": "https://pfaf.org/"},
    }
    assert "scientific name" in data["sources"]


def test_get_plant_detail_translated_sources(client):
    """Source keys should be translated to match characteristic keys."""
    r = client.get(
        "/permaculture/plants/symphytum officinale",
        params={"lang": "fr"},
    )
    data = r.json()
    assert "nom scientifique" in data["sources"]
    assert isinstance(data["sources"]["soleil"], dict)


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


def test_group_characteristics_non_dict():
    """Numeric-keyed input should be returned as a list."""
    data = {"0": "first", "1": "second"}
    result = group_characteristics(data)
    assert result == ["first", "second"]


def test_translate_data_non_dict():
    """Non-dict input should be returned as-is."""
    assert translate_data([1, 2, 3], None) == [1, 2, 3]


def test_translate_data_flat():
    """Translate data should translate top-level keys."""
    locales = Locales.from_domain("api", language="fr")
    data = {"scientific name": "test", "height": 1.2}
    result = translate_data(data, locales)
    assert result == {"nom scientifique": "test", "hauteur": 1.2}


def test_translate_data_nested():
    """Translate data should recurse into nested dicts."""
    locales = Locales.from_domain("api", language="fr")
    data = {"height": {"max": 1.2}}
    result = translate_data(data, locales)
    assert result == {"hauteur": {"max": 1.2}}


def test_translate_data_passthrough():
    """Untranslated keys should pass through unchanged."""
    locales = Locales.from_domain("api", language="fr")
    data = {"unknown key": 42}
    result = translate_data(data, locales)
    assert result == {"unknown key": 42}


def test_translate_data_string_values():
    """Translate data should translate string values using context."""
    locales = Locales.from_domain("api", language="fr")
    data = {"growth rate": "fast"}
    result = translate_data(data, locales)
    assert result == {"taux de croissance": "rapide"}


def test_translate_data_list_values():
    """Translate data should translate list items using context."""
    locales = Locales.from_domain("api", language="fr")
    data = {"sun": ["full", "partial"]}
    result = translate_data(data, locales)
    assert result == {"soleil": ["plein soleil", "mi-ombre"]}

