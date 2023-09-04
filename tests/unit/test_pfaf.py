"""Unit tests for the pfaf module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from permaculture.iterator import IteratorElement
from permaculture.pfaf import Pfaf, apply_legend, iterator


def test_pfaf_main_database():
    """The main database should return the corresponding Excel worksheet."""
    path = Path(__file__).with_suffix(".xls")
    storage = Mock(key_to_path=Mock(return_value=path))
    pfaf = Pfaf(storage)
    ws = pfaf.main_database()
    assert ws.cell(0, 0).value == "Test"


@pytest.mark.parametrize(
    "row, expected",
    [
        pytest.param(
            {"Soil": "LMH"},
            {"Soil": ["Light(sandy)", "Medium(loam)", "Heavy"]},
            id="Soil",
        ),
        pytest.param(
            {"Shade": "FSN"},
            {"Shade": ["Full", "Semi", "None"]},
            id="Shade",
        ),
        pytest.param(
            {"pH": "ANB"},
            {"pH": ["Acid", "Neutral", "Base/Alkaline"]},
            id="pH",
        ),
    ],
)
def test_apply_legend(row, expected):
    """Applying the legend should translate a row into the expected result."""
    result = apply_legend(row)
    assert result == expected


@patch("permaculture.pfaf.all_plants")
def test_iterator(mock_all_plants):
    """Iterating over plants should return a list of elements."""
    mock_all_plants.return_value = [
        {
            "Latin name": "a",
            "Common name": "b",
        }
    ]

    elements = iterator("")
    assert elements == [
        IteratorElement(
            scientific_name="a",
            common_names=["b"],
            characteristics={
                "Latin name": "a",
                "Common name": "b",
            },
        )
    ]
