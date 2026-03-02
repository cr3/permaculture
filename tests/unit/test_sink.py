"""Unit tests for the sink module."""

import pytest

from permaculture.database import DatabasePlant
from permaculture.sink import SQLiteSink


@pytest.fixture
def sink(tmp_path):
    """Create a SQLiteSink backed by a temporary database."""
    s = SQLiteSink(tmp_path / "test.db")
    s.initialize()
    return s


def test_sqlite_sink_initialize(sink):
    """Initializing should create tables without error."""
    # Double-initialize should be idempotent.
    sink.initialize()


def test_sqlite_sink_write_batch_and_read_all(sink):
    """Writing a batch should persist records retrievable via read_all."""
    records = [
        DatabasePlant(
            {
                "scientific name": "symphytum officinale",
                "common name/comfrey": True,
            }
        ),
        DatabasePlant(
            {
                "scientific name": "achillea millefolium",
                "common name/yarrow": True,
            }
        ),
    ]
    sink.write_batch("pfaf", records)
    result = sink.read_all()
    assert len(result) == 2
    names = {p["scientific name"] for p in result}
    assert names == {"symphytum officinale", "achillea millefolium"}


def test_sqlite_sink_search(sink):
    """Searching should return plants matching common name substring."""
    sink.write_batch(
        "pfaf",
        [
            DatabasePlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                }
            ),
            DatabasePlant(
                {
                    "scientific name": "achillea millefolium",
                    "common name/yarrow": True,
                }
            ),
        ],
    )
    result = sink.search("comfrey")
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_sqlite_sink_search_no_match(sink):
    """Searching for a non-existent name should return empty."""
    sink.write_batch(
        "pfaf",
        [
            DatabasePlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                }
            ),
        ],
    )
    result = sink.search("nonexistent")
    assert result == []


def test_sqlite_sink_lookup(sink):
    """Lookup should return plants matching exact scientific names."""
    sink.write_batch(
        "pfaf",
        [
            DatabasePlant(
                {
                    "scientific name": "symphytum officinale",
                }
            ),
            DatabasePlant(
                {
                    "scientific name": "achillea millefolium",
                }
            ),
        ],
    )
    result = sink.lookup(["symphytum officinale"])
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_sqlite_sink_lookup_empty(sink):
    """Lookup with empty names should return empty."""
    result = sink.lookup([])
    assert result == []


def test_sqlite_sink_weight_preserved(sink):
    """Weight should be preserved through write and read."""
    sink.write_batch(
        "pfaf",
        [
            DatabasePlant({"scientific name": "test"}, weight=2.5),
        ],
    )
    result = sink.read_all()
    assert result[0].weight == 2.5
