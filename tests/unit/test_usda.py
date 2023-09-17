"""Unit tests for the USDA module."""

from unittest.mock import ANY, Mock

from permaculture.database import DatabaseElement
from permaculture.storage import MemoryStorage
from permaculture.usda import (
    USDADatabase,
    USDAModel,
    USDAWeb,
)

from .stubs import StubRequestsResponse


def test_usda_web_characteristics_search():
    """CharacteristicsSearch should POST a JSON payload."""
    client = Mock(post=Mock(return_value=StubRequestsResponse()))
    USDAWeb(client).characteristics_search()
    client.post.assert_called_once_with(
        "/api/CharacteristicsSearch",
        json=ANY,
    )


def test_usda_web_plant_profile():
    """PlantProfile should GET with the symbol query param."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    USDAWeb(client).plant_profile("test")
    client.get.assert_called_once_with(
        "/api/PlantProfile",
        params={"symbol": "test"},
    )


def test_usda_web_plant_characteristics():
    """PlantCharacteristics should GET with the id in the URL."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    USDAWeb(client).plant_characteristics(1234)
    client.get.assert_called_once_with("/api/PlantCharacteristics/1234")


def test_usda_model_all_characteristics():
    """All characteristics should return the general characteristics."""
    web = Mock(
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
    storage = MemoryStorage()
    characteristics = USDAModel(web, storage).all_characteristics()
    assert characteristics == [
        {
            "id": "1",
            "scientific name": "a",
            "common name": "b",
        }
    ]


def test_usda_database_iterate():
    """Iterating over the database should return a list of elements."""
    model = Mock(
        all_characteristics=Mock(
            return_value=[
                {
                    "id": "1",
                    "scientific name": "a",
                    "common name": "b",
                }
            ]
        )
    )

    database = USDADatabase(model)
    elements = list(database.iterate())
    assert elements == [
        DatabaseElement(
            database="USDA",
            scientific_name="a",
            common_names=["b"],
            characteristics={
                "id": "1",
                "scientific name": "a",
                "common name": "b",
            },
        )
    ]
