"""Integration tests for the local module."""

from pathlib import Path

from permaculture.local import LocalIngestor

PLANTS_PATH = Path(__file__).parent / "fixtures" / "plants.json"


def test_local_fetch_all():
    """Fetching all plants from a local file should return each file."""
    ingestor = LocalIngestor("Test", path=PLANTS_PATH)
    plants = list(ingestor.fetch_all())

    assert len(plants) == 2
    assert plants[0].scientific_name == "symphytum officinale"
    assert plants[1].scientific_name == "achillea millefolium"
