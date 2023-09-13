"""Unit tests for the pfaf module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from permaculture.database import DatabaseElement
from permaculture.pfaf import Pfaf, all_plants, apply_legend, pfaf_database


def test_pfaf_main_database():
    """The main database should return the corresponding Excel worksheet."""
    path = Path(__file__).with_suffix(".xls")
    storage = Mock(key_to_path=Mock(return_value=path))
    pfaf = Pfaf(storage)
    ws = pfaf.main_database()
    assert ws.cell(0, 0).value == "Test"


def test_pfaf_main_database_error(tmpdir):
    """The main database should raise when file not found."""
    pfaf = Pfaf.with_cache_dir(tmpdir)
    with pytest.raises(FileNotFoundError):
        pfaf.main_database()


def test_all_plants_error(tmpdir):
    """All plants should return no plant when file not found."""
    pfaf = Pfaf.with_cache_dir(tmpdir)
    plants = all_plants(pfaf)
    assert plants == []


@pytest.mark.parametrize(
    "row, expected",
    [
        pytest.param(
            {"Deciduous/Evergreen": "DE"},
            {
                "Deciduous/Evergreen": [
                    "Deciduous",
                    "Evergreen",
                ]
            },
            id="Deciduous/Evergreen",
        ),
        pytest.param(
            {"pH": "ANB"},
            {"pH": ["Acid", "Neutral", "Base/Alkaline"]},
            id="pH",
        ),
        pytest.param(
            {"Shade": "FSN"},
            {"Shade": ["Full", "Semi", "None"]},
            id="Shade",
        ),
        pytest.param(
            {"Soil": "LMH"},
            {"Soil": ["Light(sandy)", "Medium(loam)", "Heavy"]},
            id="Soil",
        ),
    ],
)
def test_apply_legend(row, expected):
    """Applying the legend should translate a row into the expected result."""
    result = apply_legend(row)
    assert result == expected


@patch("permaculture.pfaf.all_plants")
def test_pfaf_database_iterate(mock_all_plants):
    """Iterating over the database should return a list of elements."""
    mock_all_plants.return_value = [
        {
            "Latin name": "a",
            "Common name": "b",
        }
    ]

    elements = pfaf_database.iterate("")
    assert elements == [
        DatabaseElement(
            database="PFAF",
            scientific_name="a",
            common_names=["b"],
            characteristics={
                "Latin name": "a",
                "Common name": "b",
            },
        )
    ]
