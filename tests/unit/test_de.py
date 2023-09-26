"""Unit tests for the Design Ecologique module."""

from unittest.mock import Mock

import pytest

from permaculture.de import (
    DEConverter,
    DEDatabase,
    DEModel,
    DEWeb,
)

from .stubs import StubRequestsResponse


def test_de_web_perenial_plants_list(unique):
    """Perenial plants should GET and return the spreadsheet."""
    doc_id = unique("text")
    text = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit'>"
    session = Mock(get=Mock(return_value=StubRequestsResponse(text=text)))
    plants = DEWeb(session).perenial_plants_list()
    session.get.assert_called_once_with("/liste-de-plantes-vivaces/")
    assert plants.doc_id == doc_id


def test_de_web_perenial_plants_list_error():
    """Perenial plants should raise when spreadhseet is not found."""
    session = Mock(get=Mock(return_value=StubRequestsResponse()))
    with pytest.raises(KeyError):
        DEWeb(session).perenial_plants_list()


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "value",
            "value",
        ),
        (
            "*",
            None,
        ),
    ],
)
def test_de_converter_translate(value, expected):
    """Translating * should return None."""
    result = DEConverter().translate(value)
    assert result == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("X", True),
        ("*", False),
        ("", None),
    ],
)
def test_de_converter_convert_bool(value, expected):
    """Converting a bool should return the True, False, or None."""
    result = DEConverter().convert_bool("", value)
    assert result == [("", expected)]


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("Accumulateur de Nutriments", "*"),
            [],
            id="nutriments",
        ),
        pytest.param(
            ("Comestible", "Fl,Fr,Fe,N,G,R,S,JP,T,B"),
            [
                ("edible uses/flower", True),
                ("edible uses/fruit", True),
                ("edible uses/leaf", True),
                ("edible uses/nut", True),
                ("edible uses/seed", True),
                ("edible uses/root", True),
                ("edible uses/sap", True),
                ("edible uses/young shoot", True),
                ("edible uses/stem", True),
                ("edible uses/bulb", True),
            ],
            id="edible uses",
        ),
        pytest.param(
            ("Couleur de feuillage", "V Po Pa P F T J"),
            [
                ("foliage color/green", True),
                ("foliage color/purple", True),
                ("foliage color/variegated", True),
                ("foliage color/pale", True),
                ("foliage color/dark", True),
                ("foliage color/spotted", True),
                ("foliage color/yellow", True),
            ],
            id="foliage color",
        ),
        pytest.param(
            ("Couleur de floraison", "Rg Rs B J O P V Br Bl"),
            [
                ("flower color/red", True),
                ("flower color/pink", True),
                ("flower color/white", True),
                ("flower color/yellow", True),
                ("flower color/orange", True),
                ("flower color/purple", True),
                ("flower color/green", True),
                ("flower color/brown", True),
                ("flower color/blue", True),
            ],
            id="flower color",
        ),
        pytest.param(
            ("Couvre-sol", "*"),
            [],
            id="ground cover",
        ),
        pytest.param(
            ("Cultivars intéressants", "*"),
            [],
            id="cultivars",
        ),
        pytest.param(
            ("Eau", "▁ ▅ █"),
            [
                ("moisture/dry", True),
                ("moisture/moderate", True),
                ("moisture/wet", True),
            ],
            id="moisture",
        ),
        pytest.param(
            ("Haie", "*"),
            [],
            id="hedge",
        ),
        pytest.param(
            ("Hauteur(m)", "0,6 \u2013 1,2"),
            [
                ("height/min", 0.6),
                ("height/max", 1.2),
            ],
            id="height with endash",
        ),
        pytest.param(
            ("Inconvénient", "E D A P Épi V B G Pe"),
            [
                ("inconvenience/expansive", True),
                ("inconvenience/dispersive", True),
                ("inconvenience/allergen", True),
                ("inconvenience/poison", True),
                ("inconvenience/thorny", True),
                ("inconvenience/vigorous", True),
                ("inconvenience/burns", True),
                ("inconvenience/invasive", True),
                ("inconvenience/persistent", True),
            ],
            id="inconvenience",
        ),
        pytest.param(
            ("Intérêt automnale hivernal", "A H"),
            [],
            id="interest",
        ),
        pytest.param(
            ("Largeur(m)", "1,0"),
            [
                ("spread/min", 1.0),
                ("spread/max", 1.0),
            ],
            id="spread with only minimum",
        ),
        pytest.param(
            ("Lien Information", ""),
            [],
            id="information",
        ),
        pytest.param(
            ("Lumière", "○ ◐ ●"),
            [
                ("sun/full", True),
                ("sun/partial", True),
                ("sun/shade", True),
            ],
            id="sun",
        ),
        pytest.param(
            ("Multiplication", "B M D S G St P A É T"),
            [
                ("multiplication/cuttings", True),
                ("multiplication/layering", True),
                ("multiplication/division", True),
                ("multiplication/seeds", True),
                ("multiplication/graft", True),
                ("multiplication/stolon", True),
                ("multiplication/spring", True),
                ("multiplication/autumn", True),
                ("multiplication/summer", True),
                ("multiplication/tuber", True),
            ],
            id="Multiplication",
        ),
        pytest.param(
            ("Période de floraison", "P É A"),
            [
                ("bloom period/min", "spring"),
                ("bloom period/max", "autumn"),
            ],
            id="bloom period",
        ),
        pytest.param(
            ("Période de taille", "AD,AF,P,É,A,T,N"),
            [
                ("pruning period/before budburst", True),
                ("pruning period/after flowering", True),
                ("pruning period/spring", True),
                ("pruning period/summer", True),
                ("pruning period/autumn", True),
                ("pruning period/at all times", True),
                ("pruning period/never prune", True),
            ],
            id="pruning period",
        ),
        pytest.param(
            ("Pollinisateurs", "S G V"),
            [
                ("pollinators/specialists", True),
                ("pollinators/generalists", True),
                ("pollinators/wind", True),
            ],
            id="pollinators",
        ),
        pytest.param(
            ("Racine", "B C D F L P R S T"),
            [
                ("root type/bulb", True),
                ("root type/fleshy", True),
                ("root type/suckering", True),
                ("root type/fasciculated", True),
                ("root type/lateral", True),
                ("root type/taproot", True),
                ("root type/rhizome", True),
                ("root type/superficial", True),
                ("root type/tuber", True),
            ],
            id="root type",
        ),
        pytest.param(
            ("Rythme de croissance", "R M L"),
            [
                ("growth rate/fast", True),
                ("growth rate/medium", True),
                ("growth rate/slow", True),
            ],
            id="growth rate",
        ),
        pytest.param(
            ("Texture du sol", "░ ▒ ▓"),
            [
                ("soil/light", True),
                ("soil/medium", True),
                ("soil/heavy", True),
            ],
            id="soil",
        ),
        pytest.param(
            ("Utilisation écologique", "BR,P,Z"),
            [
                ("ecological use/riparian strip", True),
                ("ecological use/slopes", True),
                ("ecological use/flood zone", True),
            ],
            id="ecological use",
        ),
        pytest.param(
            ("Vie sauvage", "N A"),
            [
                ("wildlife/food", True),
                ("wildlife/shelter", True),
            ],
            id="wildlife",
        ),
        pytest.param(
            ("pH (Min-Max)", "6 - 7"),
            [
                ("ph/min", 6.0),
                ("ph/max", 7.0),
            ],
            id="ph with dash",
        ),
    ],
)
def test_de_converter_convert_item(item, expected):
    """Converting an item should consider types."""
    result = DEConverter().convert_item(*item)
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
                    "english name": "c",
                    "french name": "d",
                }
            ]
        )
    )

    database = DEDatabase(model)
    elements = list(database.iterate())
    assert elements == [
        {
            "scientific name": "a b",
            "common name": ["c", "d"],
        },
    ]
