"""Unit tests for the FastAPI app module."""

import pytest
from fastapi.testclient import TestClient

from permaculture.app import app, group_characteristics, state, translate_keys
from permaculture.database import Database, DatabasePlant
from permaculture.locales import Locales


@pytest.fixture
def client(tmp_path):
    """Create a test client backed by a temporary database."""
    db_path = tmp_path / "permaculture.db"
    database = Database(db_path)
    database.initialize()
    database.write_batch(
        "test",
        [
            DatabasePlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                    "height/max": 1.2,
                }
            ),
            DatabasePlant(
                {
                    "scientific name": "achillea millefolium",
                    "common name/yarrow": True,
                    "height/max": 0.6,
                }
            ),
        ],
    )
    state.database = Database(db_path)
    yield TestClient(app)
    state.database = None


def test_index_returns_html(client):
    """The root should return the typeahead HTML page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Plant Search" in response.text


def test_suggest_by_scientific_name(client):
    """Suggest should match scientific names."""
    response = client.get("/api/plants", params={"q": "symphytum"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["scientific_name"] == "symphytum officinale"


def test_suggest_by_common_name(client):
    """Suggest should match common names."""
    response = client.get("/api/plants", params={"q": "yarrow"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["scientific_name"] == "achillea millefolium"
    assert "yarrow" in results[0]["common_names"]


def test_suggest_empty_query(client):
    """Suggest should reject an empty query."""
    response = client.get("/api/plants", params={"q": ""})
    assert response.status_code == 422


def test_suggest_no_match(client):
    """Suggest should return empty for unknown names."""
    response = client.get("/api/plants", params={"q": "zzzzz"})
    assert response.status_code == 200
    assert response.json() == []


def test_suggest_limit(client):
    """Suggest should respect the limit parameter."""
    response = client.get("/api/plants", params={"q": "a", "limit": 1})
    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_lookup_found(client):
    """Lookup should return full characteristics for a known plant."""
    response = client.get("/api/plants/symphytum officinale")
    assert response.status_code == 200
    data = response.json()
    assert data["scientific name"] == "symphytum officinale"
    assert data["common name"] == ["comfrey"]
    assert data["height"] == {"max": 1.2}


def test_lookup_not_found(client):
    """Lookup should return empty for an unknown plant."""
    response = client.get("/api/plants/nonexistent plant")
    assert response.status_code == 200
    assert response.json() == {}


def test_suggest_no_database():
    """Suggest should return empty when no database is loaded."""
    state.database = None
    client = TestClient(app)
    response = client.get("/api/plants", params={"q": "test"})
    assert response.status_code == 200
    assert response.json() == []


def test_lookup_no_database():
    """Lookup should return empty when no database is loaded."""
    state.database = None
    client = TestClient(app)
    response = client.get("/api/plants/test")
    assert response.status_code == 200
    assert response.json() == {}


def test_translate_keys_flat():
    """Translate keys should translate top-level keys."""
    locales = Locales.from_domain("display", language="fr")
    data = {"scientific name": "test", "height": 1.2}
    result = translate_keys(data, locales)
    assert result == {"nom scientifique": "test", "hauteur": 1.2}


def test_translate_keys_nested():
    """Translate keys should recurse into nested dicts."""
    locales = Locales.from_domain("display", language="fr")
    data = {"height": {"max": 1.2}}
    result = translate_keys(data, locales)
    assert result == {"hauteur": {"max": 1.2}}


def test_translate_keys_passthrough():
    """Untranslated keys should pass through unchanged."""
    locales = Locales.from_domain("display", language="fr")
    data = {"unknown key": 42}
    result = translate_keys(data, locales)
    assert result == {"unknown key": 42}


def test_lookup_french(client):
    """Lookup with French Accept-Language should translate keys."""
    response = client.get(
        "/api/plants/symphytum officinale",
        headers={"Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nom scientifique"] == "symphytum officinale"
    assert data["nom commun"] == ["comfrey"]
    assert data["hauteur"] == {"max": 1.2}


def test_group_characteristics_bool_subkeys():
    """Boolean sub-keys should be grouped into a sorted list."""
    data = {"sun/partial": True, "sun/full": True}
    result = group_characteristics(data)
    assert result == {"sun": ["full", "partial"]}


def test_group_characteristics_mixed_subkeys():
    """Non-boolean sub-keys should remain as dicts."""
    data = {"height/max": 1.2, "height/min": 0.5}
    result = group_characteristics(data)
    assert result == {"height": {"max": 1.2, "min": 0.5}}
