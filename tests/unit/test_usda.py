"""Unit tests for the USDA module."""

from unittest.mock import ANY, Mock, patch

from permaculture.database import DatabaseElement
from permaculture.usda import (
    USDAPlants,
    USDAPlantsDatabase,
    all_characteristics,
)

from .stubs import StubRequestsResponse


def test_usda_plants_characteristics_search():
    """CharacteristicsSearch should POST a JSON payload."""
    client = Mock(post=Mock(return_value=StubRequestsResponse()))
    USDAPlants(client).characteristics_search()
    client.post.assert_called_once_with(
        "/api/CharacteristicsSearch",
        json=ANY,
    )


def test_usda_plants_plant_profile():
    """PlantProfile should GET with the symbol query param."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    USDAPlants(client).plant_profile("test")
    client.get.assert_called_once_with(
        "/api/PlantProfile",
        params={"symbol": "test"},
    )


def test_usda_plants_plant_characteristics():
    """PlantCharacteristics should GET with the id in the URL."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    USDAPlants(client).plant_characteristics(1234)
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
def test_usda_database_iterate(mock_all_characteristics):
    """Iterating over the database should return a list of elements."""
    mock_all_characteristics.return_value = [
        {
            "General/Id": "1",
            "General/ScientificName": "a",
            "General/CommonName": "b",
        }
    ]

    database = USDAPlantsDatabase.from_config(Mock(cache_dir=""))
    elements = list(database.iterate())
    assert elements == [
        DatabaseElement(
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
