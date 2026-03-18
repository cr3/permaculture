"""Unit tests for the database module."""

import pytest

from permaculture.database import (
    Database,
    _merge,
    _merge_all,
)
from permaculture.plant import DatabasePlant, IngestorPlant


def test_database_from_url_file(tmp_path):
    """Creating from a file path should use that path."""
    db_path = tmp_path / "test.db"
    db = Database.from_url(str(db_path))
    db.initialize()
    assert db_path.exists()


def test_database_from_url_memory():
    """Creating from :memory: should produce a working database."""
    db = Database.from_url(":memory:")
    db.initialize()
    result = list(db.iterate())
    assert result == []


def test_database_plant_ingestor():
    """IngestorPlant should support the ingestor field."""
    plant = IngestorPlant({"scientific name": "a"}, 1.0, ingestor="pfaf", title="Plants For A Future", source="x")
    assert plant.ingestor == "pfaf"


def test_database_ingestors(database):
    """Ingestors should list distinct ingestor names."""
    database.write_batch([IngestorPlant({"scientific name": "x"}, 1.0, ingestor="a", title="A", source="s")])
    database.write_batch([IngestorPlant({"scientific name": "y"}, 1.0, ingestor="b", title="B", source="s")])

    assert sorted(database.ingestors()) == ["a", "b"]


def test_database_ingestors_filtered(database):
    """Ingestors should filter by regex when provided."""
    database.write_batch([IngestorPlant({"scientific name": "x"}, 1.0, ingestor="a", title="A", source="s")])
    database.write_batch([IngestorPlant({"scientific name": "y"}, 1.0, ingestor="b", title="B", source="s")])

    import re

    include = re.compile("a", re.I)
    assert database.ingestors(include) == ["a"]


def test_database_iterate(database):
    """Iterating should return all plants from the local database."""
    database.write_batch([IngestorPlant({"scientific name": "x"}, 1.0, ingestor="a", title="A", source="s")])

    result = list(database.iterate())
    assert len(result) == 1
    assert result[0]["scientific name"] == "x"


def test_database_lookup(database):
    """Lookup should return plants matching scientific names."""
    database.write_batch(
        [
            IngestorPlant(
                {"scientific name": "symphytum officinale"}, 1.0, ingestor="a", title="A", source="s"
            ),
            IngestorPlant(
                {"scientific name": "achillea millefolium"}, 1.0, ingestor="a", title="A", source="s"
            ),
        ],
    )

    result = list(database.lookup(["symphytum officinale"], 1.0))
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_database_search(database):
    """Search should return plants matching common name."""
    database.write_batch(
        [
            IngestorPlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                },
                1.0,
                ingestor="a", title="A",
                source="s",
            ),
        ],
    )

    result = list(database.search("comfrey", 0.5))
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_database_search_by_scientific_name(database):
    """Search should also match on scientific name via FTS5."""
    database.write_batch(
        [
            IngestorPlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                },
                1.0,
                ingestor="a", title="A",
                source="s",
            ),
        ],
    )

    result = list(database.search("symphytum", 0.5))
    assert len(result) == 1
    assert result[0]["scientific name"] == "symphytum officinale"


def test_database_iterate_merges_sources(database):
    """Iterating should merge plants from multiple ingestors."""
    database.write_batch([IngestorPlant({"scientific name": "x"}, 1.0, ingestor="a", title="A", source="s")])
    database.write_batch([IngestorPlant({"scientific name": "y"}, 1.0, ingestor="b", title="B", source="s")])

    result = list(database.iterate())
    assert len(result) == 2
    names = {p.scientific_name for p in result}
    assert names == {"x", "y"}


def test_database_iterate_tracks_source(database):
    """Iterating should track per-attribute ingestors and sources after merging."""
    database.write_batch([IngestorPlant({"scientific name": "x"}, 1.0, ingestor="pfaf", title="Plants For A Future", source="https://pfaf.org/")])

    result = list(database.iterate())
    assert result[0].ingestors == {"pfaf": {"title": "Plants For A Future", "source": "https://pfaf.org/"}}
    assert result[0].sources == {"scientific name": ["pfaf"]}


@pytest.mark.parametrize(
    "plants, expected",
    [
        pytest.param(
            [],
            [],
            id="empty",
        ),
        pytest.param(
            [IngestorPlant({"scientific name": "a"}, 1.0, ingestor="s1", title="S1", source="u1")],
            [
                DatabasePlant(
                    {"scientific name": "a"},
                    1.0,
                    ingestors={"s1": {"title": "S1", "source": "u1"}},
                    sources={"scientific name": ["s1"]},
                ),
            ],
            id="single",
        ),
        pytest.param(
            [
                IngestorPlant({"scientific name": "a"}, 1.0, ingestor="s1", title="S1", source="u1"),
                IngestorPlant({"scientific name": "a"}, 1.0, ingestor="s2", title="S2", source="u2"),
            ],
            [
                DatabasePlant(
                    {"scientific name": "a"},
                    1.0,
                    ingestors={"s1": {"title": "S1", "source": "u1"}, "s2": {"title": "S2", "source": "u2"}},
                    sources={"scientific name": ["s1", "s2"]},
                ),
            ],
            id="group by scientific name",
        ),
    ],
)
def test_database_merge_all(plants, expected):
    """Merging all plants should group by scientific name."""
    result = list(_merge_all(plants))
    assert result == expected


@pytest.mark.parametrize(
    "plants, expected",
    [
        pytest.param(
            [],
            DatabasePlant({}, 1.0, ingestors={}, sources={}),
            id="empty",
        ),
        pytest.param(
            [IngestorPlant({"scientific name": "a"}, 1.0, ingestor="s1", title="S1", source="u1")],
            DatabasePlant(
                {"scientific name": "a"},
                1.0,
                ingestors={"s1": {"title": "S1", "source": "u1"}},
                sources={"scientific name": ["s1"]},
            ),
            id="single",
        ),
        pytest.param(
            [
                IngestorPlant({"scientific name": "a"}, 1.0, ingestor="s1", title="S1", source="u1"),
                IngestorPlant({"scientific name": "a"}, 1.0, ingestor="s2", title="S2", source="u2"),
            ],
            DatabasePlant(
                {"scientific name": "a"},
                1.0,
                ingestors={"s1": {"title": "S1", "source": "u1"}, "s2": {"title": "S2", "source": "u2"}},
                sources={"scientific name": ["s1", "s2"]},
            ),
            id="group by scientific name",
        ),
        pytest.param(
            [
                IngestorPlant({"scientific name": "a", "x": 1}, 2.0, ingestor="s1", title="S1", source="u1"),
                IngestorPlant({"scientific name": "a", "x": 4}, 1.0, ingestor="s2", title="S2", source="u2"),
            ],
            DatabasePlant(
                {"scientific name": "a", "x": 2.0},
                1.5,
                ingestors={"s1": {"title": "S1", "source": "u1"}, "s2": {"title": "S2", "source": "u2"}},
                sources={"scientific name": ["s1", "s2"], "x": ["s1", "s2"]},
            ),
            id="merge numbers",
        ),
        pytest.param(
            [
                IngestorPlant({"scientific name": "a", "x": "b"}, 2.0, ingestor="s1", title="S1", source="u1"),
                IngestorPlant({"scientific name": "a", "x": "c"}, 1.0, ingestor="s2", title="S2", source="u2"),
            ],
            DatabasePlant(
                {"scientific name": "a", "x": "b"},
                1.5,
                ingestors={"s1": {"title": "S1", "source": "u1"}, "s2": {"title": "S2", "source": "u2"}},
                sources={"scientific name": ["s1", "s2"], "x": ["s1", "s2"]},
            ),
            id="merge strings",
        ),
    ],
)
def test_database_merge(plants, expected):
    """Merging plants should merge numbers and strings."""
    result = _merge(plants)
    assert result == expected


def test_database_initialize_idempotent(database):
    """Initializing twice should be idempotent."""
    database.initialize()


def test_database_write_batch_and_iterate(database):
    """Writing a batch should persist records retrievable via iterate."""
    records = [
        IngestorPlant(
            {
                "scientific name": "symphytum officinale",
                "common name/comfrey": True,
            },
            1.0,
            ingestor="pfaf", title="Plants For A Future",
            source="https://pfaf.org/",
        ),
        IngestorPlant(
            {
                "scientific name": "achillea millefolium",
                "common name/yarrow": True,
            },
            1.0,
            ingestor="pfaf", title="Plants For A Future",
            source="https://pfaf.org/",
        ),
    ]
    database.write_batch(records)
    result = list(database.iterate())
    assert len(result) == 2
    names = {p["scientific name"] for p in result}
    assert names == {"symphytum officinale", "achillea millefolium"}


def test_database_search_no_match(database):
    """Searching for a non-existent name should return empty."""
    database.write_batch(
        [
            IngestorPlant(
                {
                    "scientific name": "symphytum officinale",
                    "common name/comfrey": True,
                },
                1.0,
                ingestor="pfaf", title="Plants For A Future",
                source="https://pfaf.org/",
            ),
        ],
    )
    result = list(database.search("nonexistent", 0.5))
    assert result == []


def test_database_lookup_empty(database):
    """Lookup with empty names should return empty."""
    result = list(database.lookup([], 1.0))
    assert result == []


def test_database_weight_preserved(database):
    """Weight should be preserved through write and read."""
    database.write_batch(
        [
            IngestorPlant({"scientific name": "test"}, weight=2.5, ingestor="pfaf", title="Plants For A Future", source="https://pfaf.org/"),
        ],
    )
    result = list(database.iterate())
    assert result[0].weight == 2.5


def test_database_delete_ingestor(database):
    """Deleting an ingestor should remove its plants, common names, and FTS entries."""
    database.write_batch(
        [
            IngestorPlant(
                {"scientific name": "x", "common name/comfrey": True},
                1.0,
                ingestor="a",
                title="A",
                source="s",
            ),
            IngestorPlant({"scientific name": "y"}, 1.0, ingestor="b", title="B", source="s"),
        ],
    )
    database.delete_ingestor("a")

    result = list(database.iterate())
    assert len(result) == 1
    assert result[0]["scientific name"] == "y"

    assert database.search("comfrey", 0.5) is not None
    assert list(database.search("comfrey", 0.5)) == []


def test_database_write_batch_idempotent(database):
    """Writing the same batch twice should not create duplicates."""
    records = [
        IngestorPlant({"scientific name": "x"}, 1.0, ingestor="a", title="A", source="s"),
    ]
    database.write_batch(records)
    database.write_batch(records)

    result = list(database.iterate())
    assert len(result) == 1


def test_database_write_batch_replaces_data(database):
    """Writing a record with the same key should update data."""
    database.write_batch(
        [IngestorPlant({"scientific name": "x", "height": 1.0}, 1.0, ingestor="a", title="A", source="s")],
    )
    database.write_batch(
        [IngestorPlant({"scientific name": "x", "height": 2.0}, 1.0, ingestor="a", title="A", source="s")],
    )

    result = list(database.iterate())
    assert len(result) == 1
    assert result[0]["height"] == 2.0
