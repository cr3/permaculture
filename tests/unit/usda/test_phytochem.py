"""Unit tests for the USDA Phytochem module."""

from textwrap import dedent
from unittest.mock import ANY, Mock, patch

import pytest

from permaculture.usda.phytochem import (
    PhytochemConverter,
    PhytochemDatabase,
    PhytochemEthnoplant,
    PhytochemLink,
    PhytochemModel,
    PhytochemPlant,
    PhytochemWeb,
)

from ..stubs import StubRequestsResponse


@pytest.mark.parametrize(
    "Id, Type, path, params",
    [
        pytest.param(
            11458,
            "ethnoplants",
            "/phytochem/download/11458",
            {
                "filetype": "csv",
                "name": "",
                "order": "asc",
                "type": "ethnoplants",
            },
            id="ethnoplant",
        ),
        pytest.param(
            6847,
            "plants",
            "/phytochem/download/6847",
            {
                "filetype": "csv",
                "name": "",
                "order": "asc",
                "type": "plants",
            },
            id="plant",
        ),
    ],
)
def test_phytochem_web_download(Id, Type, path, params):
    """Downloading should include the Id in the path and default params."""
    session = Mock(post=Mock(return_value=StubRequestsResponse()))
    PhytochemWeb(session).download(Id, Type)
    session.get.assert_called_once_with(
        path,
        params=params,
    )


def test_phytochem_web_search_results(unique):
    """Searching for results should pass the type and query."""
    session = Mock(post=Mock(return_value=StubRequestsResponse()))
    params = {"q": unique("text"), "et": unique("text"), "offset": 0}
    PhytochemWeb(session).search_results(**params)
    session.get.assert_called_once_with(
        "/phytochem/search-results",
        params=params,
    )


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("use/name", True),
            [
                ("use/name", True),
            ],
            id="use/name",
        ),
        pytest.param(
            ("use/name(detail)", True),
            [
                ("use/name_detail", True),
            ],
            id="use/name(detail)",
        ),
        pytest.param(
            ("chemical/name", 0),
            [
                ("chemical/name", 0),
            ],
            id="chemical/name",
        ),
        pytest.param(
            ("chemical/(-)-name", 0),
            [
                ("chemical/name_right", 0),
            ],
            id="chemical/(-)-name",
        ),
        pytest.param(
            ("chemical/(+)-name", 0),
            [
                ("chemical/name_left", 0),
            ],
            id="chemical/(+)-name",
        ),
    ],
)
def test_phytochem_converter_convert_item(item, expected):
    """Converting an item should consider use and chemical types."""
    result = PhytochemConverter().convert_item(*item)
    assert result == expected


def test_phytochem_model_download_csv():
    """Downloading a CSV should return a list of dicts."""
    with patch.object(PhytochemWeb, "download") as mock_download:
        mock_download.return_value = "col\nval\n"
        web = PhytochemWeb(None)
        model = PhytochemModel(web)
        csv = list(model.download_csv(None, None))

        assert csv == [{"col": "val"}]


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(
            dedent("""\
            <div class="entity etE">
              <a href="/phytochem/ethnoplants/show/21069">Test</a>
            </div>
            """),
            [
                PhytochemEthnoplant(21069, "ethnoplants", "Test", [], ANY),
            ],
            id="ethnoplants",
        ),
        pytest.param(
            dedent("""\
            <div class="entity etP">
              <a href="/phytochem/plants/show/6843">Test</a>
            </div>
            """),
            [
                PhytochemPlant(6843, "plants", "Test", [], ANY),
            ],
            id="plants",
        ),
        pytest.param(
            dedent("""\
            <div class="entity etP">
              <a href="/phytochem/plants/show/6843">Test</a>
              (a; b)
            </div>
            """),
            [
                PhytochemPlant(6843, "plants", "Test", ["a", "b"], ANY),
            ],
            id="plants",
        ),
    ],
)
def test_phytochem_model_search(text, expected):
    """Searching for plants should parse div records."""
    with patch.object(PhytochemWeb, "search_results") as mock_search_results:
        mock_search_results.return_value = {
            "documentRecords": text,
            "lastRecord": 20,
            "records": 1,
        }
        web = PhytochemWeb(None)
        model = PhytochemModel(web)
        csv = list(model.search("Test"))

        assert csv == expected


def test_phytochem_model_search_pagination():
    """Searching should paginate through all records."""
    with patch.object(PhytochemWeb, "search_results") as mock_search_results:
        mock_search_results.side_effect = [
            {"documentRecords": "", "lastRecord": 20, "records": 21},
            {"documentRecords": "", "lastRecord": 40, "records": 21},
        ]
        web = PhytochemWeb(None)
        model = PhytochemModel(web)
        list(model.search("Test"))

        assert mock_search_results.call_count == 2


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "/phytochem/ethnoplants/show/11458",
            PhytochemEthnoplant(11458, "ethnoplants", "test", [], ANY),
        ),
        (
            "/phytochem/plants/show/6847",
            PhytochemPlant(6847, "plants", "test", [], ANY),
        ),
    ],
)
def test_phytochem_link_from_url(url, expected):
    """A Phytochem link should parse the url to return the expected type."""
    result = PhytochemLink.from_url(url, "test")
    assert result == expected


def test_phytochem_database_lookup(unique):
    """Looking up a scientific name should return a list of elements."""
    scientific_name, activity = unique("token"), unique("integer")
    link = Mock(
        scientific_name=scientific_name,
        get_plant=Mock(
            return_value={
                "scientific name": scientific_name,
                "chemical/genistein": activity,
            },
        ),
    )
    model = Mock(
        search=Mock(
            return_value=[
                link,
            ],
        ),
    )

    database = PhytochemDatabase(model)
    elements = list(database.lookup([scientific_name], 1.0))
    assert elements == [
        {
            "scientific name": scientific_name,
            "chemical/genistein": activity,
        },
    ]
