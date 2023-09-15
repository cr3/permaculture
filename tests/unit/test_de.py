"""Unit tests for the Design Ecologique module."""

from unittest.mock import Mock, patch

import pytest

from permaculture.database import DatabaseElement
from permaculture.de import (
    DesignEcologique,
    all_perenial_plants,
    apply_legend,
    de_database,
)

from .stubs import StubRequestsResponse


def test_de_resources_perenial_plants(unique):
    """Perenial plants should GET and return the spreadsheet."""
    doc_id = unique("text")
    text = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit'>"
    client = Mock(get=Mock(return_value=StubRequestsResponse(text=text)))
    plants = DesignEcologique(client).perenial_plants()
    client.get.assert_called_once_with("/liste-de-plantes-vivaces/")
    assert plants.doc_id == doc_id


def test_de_resources_perenial_plants_error():
    """Perenial plants should raise when spreadhseet is not found."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    with pytest.raises(KeyError):
        DesignEcologique(client).perenial_plants()


@pytest.mark.parametrize(
    "row, expected",
    [
        pytest.param(
            {"Comestible": "Fl Fr Fe N G R S JP T B"},
            {
                "Comestible": [
                    "Fleur",
                    "Fruit",
                    "Feuille",
                    "Noix",
                    "Graine",
                    "Racine",
                    "Sève",
                    "Jeune pousse",
                    "Tige",
                    "Bulbe",
                ]
            },
            id="Comestible",
        ),
        pytest.param(
            {"Couleur de floraison": "Rg Rs B J O P V Br Bl"},
            {
                "Couleur de floraison": [
                    "Rouge",
                    "Rose",
                    "Blanc",
                    "Jaune",
                    "Orangé",
                    "Pourpre",
                    "Verte",
                    "Brun",
                    "Bleu",
                ]
            },
            id="Couleur de floraison",
        ),
        pytest.param(
            {"Couleur de feuillage": "V Po Pa P F T J"},
            {
                "Couleur de feuillage": [
                    "Vert",
                    "Pourpre",
                    "Panaché",
                    "Pale",
                    "Foncé",
                    "Tacheté",
                    "Jaune",
                ]
            },
            id="Couleur de feuillage",
        ),
        pytest.param(
            {"Eau": "▁ ▅ █"},
            {"Eau": ["Peu", "Moyen", "Beaucoup"]},
            id="Eau",
        ),
        pytest.param(
            {"Inconvénient": "E D A P Épi V B G Pe"},
            {
                "Inconvénient": [
                    "Expansif",
                    "Dispersif",
                    "Allergène",
                    "Poison",
                    "Épineux",
                    "Vigne vigoureuse",
                    "Brûlure",
                    "Grimpant invasif",
                    "Persistant",
                ]
            },
            id="Inconvénient",
        ),
        pytest.param(
            {"Intérêt automnale hivernal": "A H"},
            {"Intérêt automnale hivernal": ["Automne", "Hivernale"]},
            id="Intérêt automnale hivernal",
        ),
        pytest.param(
            {"Lumière": "○ ◐ ●"},
            {"Lumière": ["Plein soleil", "Mi-Ombre", "Ombre"]},
            id="Lumière",
        ),
        pytest.param(
            {"Multiplication": "B M D S G St P A É T"},
            {
                "Multiplication": [
                    "Bouturage",
                    "Marcottage",
                    "Division",
                    "Semi",
                    "Greffe",
                    "Stolon",
                    "Printemps",
                    "Automne",
                    "Été",
                    "Tubercule",
                ]
            },
            id="Multiplication",
        ),
        pytest.param(
            {"Période de floraison": "P É A"},
            {"Période de floraison": ["Printemps", "Été", "Automne"]},
            id="Période de floraison",
        ),
        pytest.param(
            {"Période de taille": "AD AF P É A T N"},
            {
                "Période de taille": [
                    "Avant le débourement",
                    "Après la floraison",
                    "Printemps",
                    "Été",
                    "Automne",
                    "en tout temps",
                    "Ne pas tailler",
                ]
            },
            id="Période de taille",
        ),
        pytest.param(
            {"Pollinisateurs": "S G V"},
            {
                "Pollinisateurs": [
                    "Spécialistes",
                    "Généralistes",
                    "Vent",
                ]
            },
            id="Pollinisateurs",
        ),
        pytest.param(
            {"Racine": "B C D F L P R S T"},
            {
                "Racine": [
                    "Bulbe",
                    "Charnu",
                    "Drageonnante",
                    "Faciculé",
                    "Latérales",
                    "Pivotante",
                    "Rhizome",
                    "Superficiel",
                    "Tubercule",
                ]
            },
            id="Racine",
        ),
        pytest.param(
            {"Rythme de croissance": "R M L"},
            {"Rythme de croissance": ["Rapide", "Moyen", "Lent"]},
            id="Rythme de croissance",
        ),
        pytest.param(
            {"Texture du sol": "░ ▒ ▓"},
            {"Texture du sol": ["Léger", "Moyen", "Lourd"]},
            id="Texture du sol",
        ),
        pytest.param(
            {"Utilisation écologique": "BR P Z"},
            {
                "Utilisation écologique": [
                    "Bande Riveraine",
                    "Pentes",
                    "Zone innondable",
                ]
            },
            id="Utilisation écologique",
        ),
        pytest.param(
            {"Vie sauvage": "N A NA"},
            {"Vie sauvage": ["Nourriture", "Abris", "Nourriture et Abris"]},
            id="Vie sauvage",
        ),
    ],
)
def test_apply_legend(row, expected):
    """Applying the legend should translate a row into the expected result."""
    result = apply_legend(row)
    assert result == expected


def test_all_perenial_plants():
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


@patch("permaculture.de.all_perenial_plants")
def test_de_database_iterate(mock_all_perenial_plants):
    """Iterating over the database should return a list of elements."""
    mock_all_perenial_plants.return_value = [
        {
            "Genre": "a",
            "Espèce": "b",
            "Nom Anglais": "c",
            "Nom français": "d",
        }
    ]

    elements = de_database.iterate(None)
    assert elements == [
        DatabaseElement(
            database="DE",
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
