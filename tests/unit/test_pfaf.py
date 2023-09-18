"""Unit tests for the pfaf module."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from permaculture.database import DatabaseElement
from permaculture.pfaf import (
    PFAFDatabase,
    PFAFFile,
    PFAFModel,
)
from permaculture.storage import FileStorage


def test_pfaf_web_main_database():
    """The main database should return the corresponding Excel worksheet."""
    path = Path(__file__).with_suffix(".xls")
    storage = Mock(key_to_path=Mock(return_value=path))
    file = PFAFFile(storage)
    ws = file.main_database()
    assert ws.cell(0, 0).value == "Test"


def test_pfaf_web_main_database_error(tmpdir):
    """The main database should raise when file not found."""
    storage = FileStorage(tmpdir)
    file = PFAFFile(storage)
    with pytest.raises(FileNotFoundError):
        file.main_database()


def test_pfaf_model_all_plants_error(tmpdir):
    """All plants should return no plant when file not found."""
    model = PFAFModel.from_cache_dir(tmpdir)
    plants = list(model.all_plants())
    assert plants == []


@pytest.mark.parametrize(
    "key_value, expected",
    [
        pytest.param(
            ("Deciduous/Evergreen", "DE"),
            (
                "deciduous/evergreen",
                [
                    "deciduous",
                    "evergreen",
                ],
            ),
            id="Deciduous/Evergreen",
        ),
        pytest.param(
            ("Growth rate", "SMF"),
            ("growth rate", ["slow", "medium", "fast"]),
            id="Growth rate",
        ),
        pytest.param(
            ("Moisture", "DMWeWa"),
            ("moisture", ["dry", "moist", "wet", "water"]),
            id="Moisture",
        ),
        pytest.param(
            ("pH", "ANB"),
            ("ph", ["acid", "neutral", "base/alkaline"]),
            id="pH",
        ),
        pytest.param(
            ("Shade", "FSN"),
            ("shade", ["full", "semi", "none"]),
            id="Shade",
        ),
        pytest.param(
            ("Soil", "LMH"),
            ("soil", ["light", "medium", "heavy"]),
            id="Soil",
        ),
    ],
)
def test_pfaf_model_convert(key_value, expected):
    """Applying the legend should translate a row into the expected result."""
    result = PFAFModel(None).convert(*key_value)
    assert result == expected


def test_pfaf_database_iterate():
    """Iterating over the database should return a list of elements."""
    model = Mock(
        all_plants=Mock(
            return_value=[
                {
                    "scientific name": "a",
                    "common name": "b",
                }
            ]
        )
    )

    database = PFAFDatabase(model)
    elements = list(database.iterate())
    assert elements == [
        DatabaseElement(
            database="PFAF",
            scientific_name="a",
            common_names=["b"],
            characteristics={
                "scientific name": "a",
                "common name": "b",
            },
        )
    ]
