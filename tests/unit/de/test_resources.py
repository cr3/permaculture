"""Unit tests for the Design Ecologique resources module."""

from unittest.mock import Mock, patch

import pytest

from permaculture.de.resources import (
    DesignEcologique,
    all_perenial_plants,
    iterator,
)
from permaculture.iterator import IteratorElement

from ..stubs import StubRequestsResponse


def test_de_resources_perenial_plants():
    """Perenial plants should GET and return the spreadsheet."""
    text = "<a href='https://docs.google.com/spreadsheets/d/test_id/edit'>"
    client = Mock(get=Mock(return_value=StubRequestsResponse(text=text)))
    plants = DesignEcologique(client).perenial_plants()
    client.get.assert_called_once_with("liste-de-plantes-vivaces")
    assert plants.doc_id == "test_id"


def test_de_resources_perenial_plants_error():
    """Perenial plants should raise when spreadhseet is not found."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    with pytest.raises(KeyError):
        DesignEcologique(client).perenial_plants()


def test_de_resources_all_perenial_plants():
    """All perenial plants should return a dictionary of characteristics."""
    data = "TAXONOMIE\nGenre,Espèce \na,b\n"
    export = Mock(return_value=data)
    perenial_plants = Mock(return_value=Mock(export=export))
    de = Mock(perenial_plants=perenial_plants)

    plants = all_perenial_plants(de)
    assert plants == [
        {
            "Genre": "a",
            "Espèce": "b",
        }
    ]


@patch("permaculture.de.resources.all_perenial_plants")
def test_de_resources_iterator(mock_all_perenial_plants):
    """Iterating over plants should return a list of elements."""
    mock_all_perenial_plants.return_value = [
        {
            "Genre": "a",
            "Espèce": "b",
            "Nom Anglais": "c",
            "Nom français": "d",
        }
    ]

    elements = iterator()
    assert elements == [
        IteratorElement(
            scientific_name="a b",
            common_names=["c", "d"],
            characteristics={
                "Genre": "a",
                "Espèce": "b",
                "Nom Anglais": "c",
                "Nom français": "d",
            },
        )
    ]
