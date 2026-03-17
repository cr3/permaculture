"""Unit tests for the local ingestor."""

import json

from permaculture.local import LocalIngestor
from permaculture.plant import IngestorPlant


def test_fetch_all(tmp_path):
    """fetch_all should yield IngestorPlant for each entry."""
    plants = [
        {"scientific name": "symphytum officinale", "height/max": 1.2},
        {"scientific name": "achillea millefolium", "height/max": 0.6},
    ]
    path = tmp_path / "plants.json"
    path.write_text(json.dumps(plants))

    ingestor = LocalIngestor("local", path=path)
    result = list(ingestor.fetch_all())

    assert len(result) == 2
    assert all(isinstance(p, IngestorPlant) for p in result)
    assert result[0].scientific_name == "symphytum officinale"
    assert result[1].scientific_name == "achillea millefolium"
    assert result[0].ingestor == "local"
    assert result[0].source == str(path)


def test_fetch_all_empty(tmp_path):
    """fetch_all should yield nothing for an empty list."""
    path = tmp_path / "plants.json"
    path.write_text("[]")

    ingestor = LocalIngestor("local", path=path)
    result = list(ingestor.fetch_all())

    assert result == []


def test_fetch_all_no_path():
    """fetch_all should yield nothing when path is None."""
    ingestor = LocalIngestor("local")
    result = list(ingestor.fetch_all())

    assert result == []


def test_from_config_with_path(tmp_path):
    """from_config should read local_path from config."""

    class Config:
        local_path = None

    config = Config()
    config.local_path = str(tmp_path / "test.json")

    ingestor = LocalIngestor.from_config(config, "local")

    assert ingestor.path == tmp_path / "test.json"


def test_from_config_without_path():
    """from_config should return a no-op ingestor when unset."""

    class Config:
        local_path = None

    ingestor = LocalIngestor.from_config(Config(), "local")

    assert ingestor.path is None
    assert list(ingestor.fetch_all()) == []
