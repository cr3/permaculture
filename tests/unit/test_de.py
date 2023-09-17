"""Unit tests for the Design Ecologique module."""

from unittest.mock import Mock

import pytest

from permaculture.database import DatabaseElement
from permaculture.de import (
    DEDatabase,
    DEModel,
    DEWeb,
)

from .stubs import StubRequestsResponse


def test_de_web_perenial_plants_list(unique):
    """Perenial plants should GET and return the spreadsheet."""
    doc_id = unique("text")
    text = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit'>"
    client = Mock(get=Mock(return_value=StubRequestsResponse(text=text)))
    plants = DEWeb(client).perenial_plants_list()
    client.get.assert_called_once_with("/liste-de-plantes-vivaces/")
    assert plants.doc_id == doc_id


def test_de_web_perenial_plants_list_error():
    """Perenial plants should raise when spreadhseet is not found."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    with pytest.raises(KeyError):
        DEWeb(client).perenial_plants_list()


@pytest.mark.parametrize(
    "key_value, expected",
    [
        pytest.param(
            ("Comestible", "Fl Fr Fe N G R S JP T B"),
            (
                "edible uses",
                [
                    "flower",
                    "fruit",
                    "leaf",
                    "nut",
                    "seed",
                    "root",
                    "sap",
                    "young shoot",
                    "stem",
                    "bulb",
                ],
            ),
            id="edible uses",
        ),
        pytest.param(
            ("Couleur de feuillage", "V Po Pa P F T J"),
            (
                "foliage color",
                [
                    "green",
                    "purple",
                    "variegated",
                    "pale",
                    "dark",
                    "spotted",
                    "yellow",
                ],
            ),
            id="foliage color",
        ),
        pytest.param(
            ("Couleur de floraison", "Rg Rs B J O P V Br Bl"),
            (
                "flower color",
                [
                    "red",
                    "pink",
                    "white",
                    "yellow",
                    "orange",
                    "purple",
                    "green",
                    "brown",
                    "blue",
                ],
            ),
            id="flower color",
        ),
        pytest.param(
            ("Eau", "▁ ▅ █"),
            ("moisture", ["dry", "moderate", "wet"]),
            id="moisture",
        ),
        pytest.param(
            ("Inconvénient", "E D A P Épi V B G Pe"),
            (
                "Inconvénient",
                [
                    "expansive",
                    "dispersive",
                    "allergen",
                    "poison",
                    "thorny",
                    "vigorous",
                    "burns",
                    "invasive",
                    "persistent",
                ],
            ),
            id="Inconvénient",
        ),
        pytest.param(
            ("Intérêt automnale hivernal", "A H"),
            ("Intérêt automnale hivernal", ["autumn", "winter"]),
            id="Intérêt automnale hivernal",
        ),
        pytest.param(
            ("Lumière", "○ ◐ ●"),
            ("sun", ["full sun", "partial shade", "shade"]),
            id="sun",
        ),
        pytest.param(
            ("Multiplication", "B M D S G St P A É T"),
            (
                "Multiplication",
                [
                    "cuttings",
                    "layering",
                    "division",
                    "seeds",
                    "graft",
                    "stolon",
                    "spring",
                    "autumn",
                    "summer",
                    "tuber",
                ],
            ),
            id="Multiplication",
        ),
        pytest.param(
            ("Période de floraison", "P É A"),
            ("blooming period", ["spring", "summer", "autumn"]),
            id="blooming period",
        ),
        pytest.param(
            ("Période de taille", "AD AF P É A T N"),
            (
                "pruning period",
                [
                    "before budburst",
                    "after flowering",
                    "spring",
                    "summer",
                    "autumn",
                    "at all times",
                    "never prune",
                ],
            ),
            id="pruning period",
        ),
        pytest.param(
            ("Pollinisateurs", "S G V"),
            (
                "pollinators",
                [
                    "specialists",
                    "generalists",
                    "wind",
                ],
            ),
            id="pollinators",
        ),
        pytest.param(
            ("Racine", "B C D F L P R S T"),
            (
                "root type",
                [
                    "bulb",
                    "fleshy",
                    "suckering",
                    "fasciculated",
                    "lateral",
                    "taproot",
                    "rhizome",
                    "superficial",
                    "tuber",
                ],
            ),
            id="root type",
        ),
        pytest.param(
            ("Rythme de croissance", "R M L"),
            ("growth rate", ["fast", "medium", "slow"]),
            id="growth rate",
        ),
        pytest.param(
            ("Texture du sol", "░ ▒ ▓"),
            ("soil", ["light", "medium", "heavy"]),
            id="soil",
        ),
        pytest.param(
            ("Utilisation écologique", "BR P Z"),
            (
                "ecological use",
                [
                    "riparian strip",
                    "slopes",
                    "flood zone",
                ],
            ),
            id="ecological use",
        ),
        pytest.param(
            ("Vie sauvage", "N A NA"),
            ("wildlife", ["food", "shelter", "food and shelter"]),
            id="wildlife",
        ),
    ],
)
def test_de_model_convert(key_value, expected):
    """Converting a key value should also translate the key and value(s)."""
    result = DEModel(None).convert(*key_value)
    assert result == expected


def test_de_model_get_perenial_plants():
    """All perenial plants should return a dictionary of characteristics."""
    data = "TAXONOMIE\nGenre,Espèce \na,b\n"
    export = Mock(return_value=data)
    perenial_plants_list = Mock(return_value=Mock(export=export))
    web = Mock(perenial_plants_list=perenial_plants_list)

    plants = list(DEModel(web).get_perenial_plants())
    assert plants == [
        {
            "genus": "a",
            "species": "b",
        }
    ]


def test_de_database_iterate():
    """Iterating over the database should return a list of elements."""
    model = Mock(
        get_perenial_plants=Mock(
            return_value=[
                {
                    "genus": "a",
                    "species": "b",
                    "common name": "c",
                }
            ]
        )
    )

    database = DEDatabase(model)
    elements = list(database.iterate())
    assert elements == [
        DatabaseElement(
            database="DE",
            scientific_name="a b",
            common_names=["c"],
            characteristics={
                "genus": "a",
                "species": "b",
                "common name": "c",
            },
        )
    ]
