"""Unit tests for the USDA Plants module."""

from unittest.mock import ANY, Mock

import pytest

from permaculture.usda.plants import (
    PlantsConverter,
    PlantsDatabase,
    PlantsModel,
    PlantsWeb,
)

from ..stubs import StubRequestsResponse


def test_plants_web_characteristics_search():
    """CharacteristicsSearch should POST a JSON payload."""
    session = Mock(post=Mock(return_value=StubRequestsResponse()))
    PlantsWeb(session).characteristics_search()
    session.post.assert_called_once_with(
        "/api/CharacteristicsSearch",
        json=ANY,
    )


def test_plants_web_plant_profile():
    """PlantProfile should GET with the symbol query param."""
    session = Mock(get=Mock(return_value=StubRequestsResponse()))
    PlantsWeb(session).plant_profile("test")
    session.get.assert_called_once_with(
        "/api/PlantProfile",
        params={"symbol": "test"},
    )


def test_plants_web_plant_characteristics():
    """PlantCharacteristics should GET with the id in the URL."""
    session = Mock(get=Mock(return_value=StubRequestsResponse()))
    PlantsWeb(session).plant_characteristics(1234)
    session.get.assert_called_once_with("/api/PlantCharacteristics/1234")


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("Adapted to Coarse Textured Soils", "Yes"),
            [("adapted to coarse textured soils", True)],
            id="Adapted to Coarse Textured Soils",
        ),
        pytest.param(
            ("Adapted to Medium Textured Soils", "Yes"),
            [("adapted to medium textured soils", True)],
            id="Adapted to Medium Textured Soils",
        ),
        pytest.param(
            ("Adapted to Medium Textured Soils", "Yes"),
            [("adapted to medium textured soils", True)],
            id="Adapted to Medium Textured Soils",
        ),
        pytest.param(
            ("Berry/Nut/Seed Product", "Yes"),
            [("berry/nut/seed product", True)],
            id="Berry/Nut/Seed Product",
        ),
        pytest.param(
            ("Christmas Tree Product", "Yes"),
            [],
            id="Christmas Tree Product",
        ),
        pytest.param(
            ("HasCharacteristics", True),
            [],
            id="HasCharacteristics",
        ),
        pytest.param(
            ("HasDistributionData", True),
            [],
            id="HasDistributionData",
        ),
        pytest.param(
            ("HasDocumentation", True),
            [],
            id="HasDocumentation",
        ),
        pytest.param(
            ("HasEthnobotany", True),
            [],
            id="HasEthnobotany",
        ),
        pytest.param(
            ("HasImages", True),
            [],
            id="HasImages",
        ),
        pytest.param(
            ("HasInvasiveStatuses", True),
            [],
            id="HasInvasiveStatuses",
        ),
        pytest.param(
            ("HasLegalStatuses", True),
            [],
            id="HasLegalStatuses",
        ),
        pytest.param(
            ("HasNoxiousStatuses", True),
            [],
            id="HasNoxiousStatuses",
        ),
        pytest.param(
            ("HasPollinator", True),
            [],
            id="HasPollinator",
        ),
        pytest.param(
            ("HasRelatedLinks", True),
            [],
            id="HasRelatedLinks",
        ),
        pytest.param(
            ("HasSubordinateTaxa", True),
            [],
            id="HasSubordinateTaxa",
        ),
        pytest.param(
            ("HasSynonyms", True),
            [],
            id="HasSynonyms",
        ),
        pytest.param(
            ("HasWetlandData", True),
            [],
            id="HasWetlandData",
        ),
        pytest.param(
            ("HasWildlife", True),
            [],
            id="HasWildlife",
        ),
    ],
)
def test_plants_converter_convert_item(item, expected):
    """Converting an item should consider types."""
    result = PlantsConverter().convert_item(*item)
    assert result == expected


def test_plants_model_all_characteristics(unique):
    """All characteristics should return the general characteristics."""
    scientific_name, common_name = unique("token"), unique("token")
    web = Mock(
        plant_characteristics=Mock(return_value={}),
        characteristics_search=Mock(
            return_value={
                "PlantResults": [
                    {
                        "Id": "1",
                        "ScientificName": scientific_name,
                        "CommonName": common_name,
                    }
                ],
            }
        ),
    )
    characteristics = list(PlantsModel(web).all_characteristics())
    assert characteristics == [
        {
            "scientific name": scientific_name,
            f"common name/{common_name}": True,
        }
    ]


def test_plants_database_iterate(unique):
    """Iterating over the database should return a list of elements."""
    scientific_name, common_name = unique("token"), unique("text")
    model = Mock(
        all_characteristics=Mock(
            return_value=[
                {
                    "scientific name": scientific_name,
                    f"common name/{common_name}": True,
                }
            ]
        )
    )

    database = PlantsDatabase(model)
    elements = list(database.iterate())
    assert elements == [
        {
            "scientific name": scientific_name,
            f"common name/{common_name}": True,
        },
    ]
