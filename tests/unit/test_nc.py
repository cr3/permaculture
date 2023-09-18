"""Unit tests for the Natural Capital module."""

import string
from textwrap import dedent
from unittest.mock import Mock, call, patch

import pytest
from yarl import URL

from permaculture.database import DatabaseElement
from permaculture.nc import (
    NCAuthentication,
    NCAuthenticationError,
    NCConverter,
    NCDatabase,
    NCLink,
    NCModel,
    NCWeb,
)

from .stubs import StubRequestsPreparedRequest, StubRequestsResponse


def test_nc_authentication_get_payload(unique):
    username, password = unique("text"), unique("password")
    value, key = unique("text"), unique("text")
    response = StubRequestsResponse(text=dedent(f"""\
        <form name="btl-formlogin">
        <input name="bttask" value="login" />
        <input name="return" value="{value}" />
        <input name="{key}" value="1" />
        </form>
    """))
    session = Mock(get=Mock(return_value=response))
    authentication = NCAuthentication(username, password, session)
    request = StubRequestsPreparedRequest()
    payload = authentication.get_payload(request)
    assert payload == {
        "bttask": "login",
        "username": username,
        "passwd": password,
        "return": value,
        key: "1",
        "remember": "yes",
    }


def test_nc_authentication_authenticate_without_cookies():
    """Authenticating without cookies in the response should raise."""
    response = StubRequestsResponse(headers={"Set-Cookie": ""})
    session = Mock(post=Mock(return_value=response))
    with patch.object(NCAuthentication, "get_payload", return_value={}):
        authentication = NCAuthentication(None, None, session)
        with pytest.raises(NCAuthenticationError):
            request = StubRequestsPreparedRequest()
            authentication.authenticate(request)


def test_nc_authentication_authenticate_with_cookies(unique):
    """Authenticating with cookies in the response should return a response."""
    cookies = unique("cookies")
    headers = {"Set-Cookie": "test"}
    response = StubRequestsResponse(headers=headers, cookies=cookies)
    session = Mock(post=Mock(return_value=response))
    with patch.object(NCAuthentication, "get_payload", return_value={}):
        authentication = NCAuthentication(None, None, session)
        request = StubRequestsPreparedRequest()
        cookie = authentication.authenticate(request)

    assert cookie == "test"


def test_nc_web_view_complist():
    """Viewing the companion list should GET with the start letter."""
    session = Mock(get=Mock(return_value=StubRequestsResponse()))
    NCWeb(session).view_complist("A")
    session.get.assert_called_once_with(
        "/plant-database/plant-companions-list",
        params={
            "vw": "complist",
            "start": "A",
        },
    )


def test_nc_web_view_detail():
    """Viewing the detail for a plant should POST with the identifier."""
    session = Mock(post=Mock(return_value=StubRequestsResponse()))
    NCWeb(session).view_detail("i")
    session.post.assert_called_once_with(
        "/plant-database/new-the-plant-list",
        params={
            "vw": "detail",
            "id": "i",
        },
    )


def test_nc_web_view_list(unique):
    """Viewing the list of plants should POST with the plant names."""
    sci_name, sort_name = unique("text"), unique("text")
    session = Mock(post=Mock(return_value=StubRequestsResponse(text="test")))
    result = NCWeb(session).view_list(sci_name, sort_name)
    session.post.assert_called_once_with(
        "/plant-database/new-the-plant-list",
        params={
            "vw": "list",
        },
        data={
            "sortName": sort_name,
            "sciName": sci_name,
            "bfilter": "Set Filter",
        },
    )
    assert result == "test"


def test_nc_converter_convert_ignore():
    """Converting an ignore item should return an empty list."""
    result = NCConverter().convert_ignore("key", "value")
    assert result == []


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("Height", "1 inches - 2 inches"),
            [
                ("height/min", 1),
                ("height/max", 2),
            ],
            id="Height",
        ),
    ],
)
def test_nc_converter_convert_range(item, expected):
    """Converting a range should support single and double values."""
    result = NCConverter().convert_range(*item)
    assert result == expected


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("Soil Type", "Sandy, Loamy"),
            [
                ("soil type/sandy", True),
                ("soil type/loamy", True),
            ],
            id="Soil Type",
        ),
        pytest.param(
            ("Sun", "Full Sun, Partial Shade"),
            [
                ("sun/full sun", True),
                ("sun/partial shade", True),
            ],
            id="Sun",
        ),
    ],
)
def test_nc_convert_convert_item(item, expected):
    """Converting an item should consider types."""
    result = NCConverter().convert_item(*item)
    assert result == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(
            dedent("""\
            <table width="100%">
              <tr>
                <td class="plantList">A</td>
              </tr>
            </table>",
        """),
            [],
            id="0 rows",
        ),
        pytest.param(
            dedent("""\
            <table width="100%">
              <tr>
                <td class="plantList">A</td>
              </tr>
              <tr>
                <td>1</td>
              </tr>
            </table>",
        """),
            [
                {"A": "1"},
            ],
            id="1 row",
        ),
        pytest.param(
            dedent("""\
            <table width="100%">
              <tr>
                <td class="plantList">A</td>
              </tr>
              <tr>
                <td><a href="http://example.com">1</a></td>
              </tr>
            </table>",
        """),
            [
                {"A": NCLink("1", URL("http://example.com"))},
            ],
            id="1 link",
        ),
    ],
)
def test_nc_model_parse_tables(text, expected):
    """Parsing tables should return a list of dictionaries."""
    model = NCModel(None)
    result = list(model.parse_tables(text))
    assert result == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(
            dedent("""\
            <table width="100%">
              <tr>
                <td><b>A</b> a</td>
              </tr>
            </table>",
        """),
            {"A": "a"},
            id="1 row",
        ),
        pytest.param(
            dedent("""\
            <table width="100%">
              <tr>
                <td><b>A</b> a</td>
              </tr>
              <tr>
                <td><b>B</b> b</td>
              </tr>
            </table>",
        """),
            {"A": "a", "B": "b"},
            id="2 rows",
        ),
        pytest.param(
            dedent("""\
            <table width="100%">
              <tr>
                <td><b>A</b> a</td>
              </tr>
              <tr>
                <td><b>B</b> b</td>
              </tr>
            </table>",
        """),
            {"A": "a", "B": "b"},
            id="2 columns",
        ),
    ],
)
def test_nc_model_parse_detail(text, expected):
    """Parsing detail should return a dictionary."""
    model = NCModel(None)
    result = model.parse_detail(text)
    assert result == expected


def test_nc_model_get_plant_companions():
    """Getting plant companions should call each letter."""
    with patch.object(NCWeb, "view_complist") as mock_complist:
        mock_complist.return_value = "<table width='100%'><tr></tr></table>"
        web = NCWeb(None)
        model = NCModel(web)
        list(model.get_plant_companions())

        assert mock_complist.call_args_list == [
            call(letter) for letter in string.ascii_uppercase
        ]


def test_nc_database_lookup():
    """Looking up a scientific name should return a list of elements."""
    model = Mock(
        get_plants=Mock(
            return_value=[
                {
                    "scientific name": "a",
                    "plant name": NCLink("b", "http://example.com/?id="),
                }
            ]
        ),
        get_plant=Mock(
            return_value={"scientific name": "a", "common name": "b"}
        ),
    )

    database = NCDatabase(model)
    elements = list(database.lookup("a"))
    assert elements == [
        DatabaseElement(
            database="NC",
            scientific_name="a",
            common_names=["b"],
            characteristics={
                "scientific name": "a",
                "common name": "b",
            },
        )
    ]


def test_nc_database_search():
    """Searching for a common name should return a list of elements."""
    model = Mock(
        get_plants=Mock(
            return_value=[
                {
                    "scientific name": "a",
                    "plant name": NCLink("b", "http://example.com/?id="),
                }
            ]
        ),
        get_plant=Mock(
            return_value={"scientific name": "a", "common name": "b"}
        ),
    )

    database = NCDatabase(model)
    elements = list(database.search("b"))
    assert elements == [
        DatabaseElement(
            database="NC",
            scientific_name="a",
            common_names=["b"],
            characteristics={
                "scientific name": "a",
                "common name": "b",
            },
        )
    ]
