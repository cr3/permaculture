"""Unit tests for the pfaf module."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from permaculture.database import DatabaseElement
from permaculture.pfaf import (
    PFAFConverter,
    PFAFDatabase,
    PFAFFile,
    PFAFModel,
)
from permaculture.storage import FileStorage


@pytest.fixture
def storage(tmpdir):
    """File storage needed for the plants database."""
    return FileStorage(tmpdir)


def test_pfaf_web_main_database():
    """The main database should return the corresponding Excel worksheet."""
    path = Path(__file__).with_suffix(".xls")
    storage = Mock(key_to_path=Mock(return_value=path))
    file = PFAFFile(storage)
    ws = file.main_database()
    assert ws.cell(0, 0).value == "Test"


def test_pfaf_web_main_database_error(storage):
    """The main database should raise when file not found."""
    file = PFAFFile(storage)
    with pytest.raises(FileNotFoundError):
        file.main_database()


def test_pfaf_converter_convert_ignore():
    """Converting an ignore item should return an empty list."""
    result = PFAFConverter().convert_ignore("key", "value")
    assert result == []


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("key", "string"),
            [("key", "string")],
            id="string",
        ),
        pytest.param(
            ("key", 1),
            [("key", 1)],
            id="int",
        ),
    ],
)
def test_pfaf_converter_convert_string(item, expected):
    """Converting a string should not convert other types."""
    result = PFAFConverter().convert_string(*item)
    assert result == expected


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
            ("Growth rate", "SMF"),
            [
                ("growth rate/slow", True),
                ("growth rate/medium", True),
                ("growth rate/fast", True),
            ],
            id="Growth rate",
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
                ("ph/base/alkaline", True),
            ],
            id="pH",
        ),
        pytest.param(
            ("Shade", "FSN"),
            [
                ("shade/full", True),
                ("shade/semi", True),
                ("shade/none", True),
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


def test_pfaf_model_all_plants_error(storage):
    """All plants should return no plant when file not found."""
    model = PFAFModel.from_storage(storage)
    plants = list(model.all_plants())
    assert plants == []


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
