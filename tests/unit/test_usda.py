"""Unit tests for the USDA module."""

from unittest.mock import ANY, Mock, patch

from permaculture.iterator import IteratorElement
from permaculture.usda import UsdaPlants, all_characteristics, iterator

from .stubs import StubRequestsResponse


def test_usda_plants_characteristics_search():
    """CharacteristicsSearch should POST a JSON payload."""
    client = Mock(post=Mock(return_value=StubRequestsResponse()))
    UsdaPlants(client).characteristics_search()
    client.post.assert_called_once_with(
        "/api/CharacteristicsSearch",
        json=ANY,
    )


def test_usda_plants_plant_profile():
    """PlantProfile should GET with the symbol query param."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    UsdaPlants(client).plant_profile("test")
    client.get.assert_called_once_with(
        "/api/PlantProfile",
        params={"symbol": "test"},
    )


def test_usda_plants_plant_characteristics():
    """PlantCharacteristics should GET with the id in the URL."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    UsdaPlants(client).plant_characteristics(1234)
    client.get.assert_called_once_with("/api/PlantCharacteristics/1234")


def test_all_characteristics():
    """All characteristics should return the general characteristics."""
    plants = Mock(
        plant_characteristics=Mock(return_value={}),
        characteristics_search=Mock(
            return_value={
                "PlantResults": [
                    {
                        "Id": "1",
                        "ScientificName": "a",
                        "CommonName": "b",
                    }
                ],
            }
        ),
    )
    characteristics = all_characteristics(plants=plants)
    assert characteristics == [
        {
            "General/Id": "1",
            "General/ScientificName": "a",
            "General/CommonName": "b",
        }
    ]


@patch("permaculture.usda.all_characteristics")
def test_iterator(mock_all_characteristics):
    """Iterating over plants should return a list of elements."""
    mock_all_characteristics.return_value = [
        {
            "General/Id": "1",
            "General/ScientificName": "a",
            "General/CommonName": "b",
        }
    ]

    elements = iterator(None)
    assert elements == [
        IteratorElement(
            database="USDA",
            scientific_name="a",
            common_names=["b"],
            characteristics={
                "General/Id": "1",
                "General/ScientificName": "a",
                "General/CommonName": "b",
            },
        )
    ]
