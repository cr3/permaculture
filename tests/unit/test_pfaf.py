"""Unit tests for the pfaf module."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from permaculture.plant import IngestorPlant
from permaculture.pfaf import (
    PFAFConverter,
    PFAFFile,
    PFAFIngestor,
    PFAFModel,
)


def test_pfaf_file_main_database():
    """The main database should return the corresponding Excel worksheet."""
    path = Path(__file__).with_suffix(".xls")
    file = PFAFFile(path)
    ws = file.main_database()
    assert ws.cell(0, 0).value == "Test"


def test_pfaf_file_main_database_error(tmp_path):
    """The main database should raise when file not found."""
    file = PFAFFile(tmp_path / "nonexistent.xls")
    with pytest.raises(FileNotFoundError):
        file.main_database()


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("1.0", 1.0, id="str"),
        pytest.param(1.0, 1.0, id="float"),
        pytest.param(1, 1.0, id="int"),
    ],
)
def test_pfaf_converter_convert_float(value, expected):
    """Converting a float should accept a float or a string."""
    result = PFAFConverter().convert_float("", value)
    assert result == [("", expected)]


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("Deciduous/Evergreen", "DE"),
            [
                ("deciduous/evergreen/deciduous", True),
                ("deciduous/evergreen/evergreen", True),
            ],
            id="Deciduous/Evergreen",
        ),
        pytest.param(
            ("Growth rate", "S"),
            [("growth rate/slow", True)],
            id="Growth rate slow",
        ),
        pytest.param(
            ("Growth rate", "M"),
            [("growth rate/medium", True)],
            id="Growth rate medium",
        ),
        pytest.param(
            ("Growth rate", "F"),
            [("growth rate/fast", True)],
            id="Growth rate fast",
        ),
        pytest.param(
            ("Moisture", "DMWeWa"),
            [
                ("moisture/dry", True),
                ("moisture/moist", True),
                ("moisture/wet", True),
                ("moisture/water", True),
            ],
            id="Moisture",
        ),
        pytest.param(
            ("pH", "ANB"),
            [
                ("ph/acid", True),
                ("ph/neutral", True),
                ("ph/alkaline", True),
            ],
            id="pH",
        ),
        pytest.param(
            ("Shade", "FSN"),
            [
                ("sun/shade", True),
                ("sun/partial", True),
                ("sun/full", True),
            ],
            id="Shade",
        ),
        pytest.param(
            ("Soil", "LMH"),
            [
                ("soil/light", True),
                ("soil/medium", True),
                ("soil/heavy", True),
            ],
            id="Soil",
        ),
    ],
)
def test_pfaf_converter_convert_item(item, expected):
    """Converting an item should consider types."""
    result = PFAFConverter().convert_item(*item)
    assert result == expected


def test_pfaf_model_all_plants_error(tmp_path):
    """All plants should return no plant when file not found."""
    model = PFAFModel.from_path(tmp_path / "nonexistent.xls")
    plants = list(model.all_plants())
    assert plants == []


def test_pfaf_ingestor_fetch_all():
    """Fetching all should return a list of elements."""
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

    ingestor = PFAFIngestor("pfaf", model)
    elements = list(ingestor.fetch_all())
    assert elements == [
        IngestorPlant(
            {
                "scientific name": "a",
                "common name": "b",
            },
            ingestor="pfaf",
        ),
    ]
