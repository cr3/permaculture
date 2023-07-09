"""Unit tests for the USDA plants module."""

from unittest.mock import ANY, Mock, patch

import pytest

from permaculture.usda.plants import UsdaPlants, main

from ..stubs import StubRequestsResponse


def test_characteristics_search():
    """CharacteristicsSearch should POST a JSON payload."""
    client = Mock(post=Mock(return_value=StubRequestsResponse()))
    UsdaPlants(client).characteristics_search()
    client.post.assert_called_once_with(
        "CharacteristicsSearch",
        json=ANY,
    )


def test_plant_profile():
    """PlantProfile should GET with the symbol query param."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    UsdaPlants(client).plant_profile("test")
    client.get.assert_called_once_with(
        "PlantProfile",
        params={"symbol": "test"},
    )


def test_plant_characteristics():
    """PlantCharacteristics should GET with the id in the URL."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    UsdaPlants(client).plant_characteristics(1234)
    client.get.assert_called_once_with("PlantCharacteristics/1234")


@patch("sys.stdout")
def test_main_help(stdout):
    """The main function should output usage when asked for --help."""
    with pytest.raises(SystemExit):
        main(["--help"])

    stdout.write.call_args[0][0].startswith("usage")
