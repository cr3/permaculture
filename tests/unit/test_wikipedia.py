"""Unit tests for the wikipedia module."""

from textwrap import dedent
from unittest.mock import Mock

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from permaculture.wikipedia import (
    Wikipedia,
    get_companion_plants,
    parse_table,
    parse_tables,
)

from .stubs import StubRequestsResponse


def test_wikipedia_get():
    """The Wikipedia get method should GET with the given action."""
    session = Mock(get=Mock(return_value=StubRequestsResponse()))
    Wikipedia(session).get("test")
    session.get.assert_called_once_with(
        "",
        params={
            "format": "json",
            "redirects": 1,
            "action": "test",
        },
    )


def test_wikipedia_get_text():
    """The Wikipedia get text method should parse the page text."""
    session = Mock(
        get=Mock(
            return_value=StubRequestsResponse(
                json=lambda: {
                    "parse": {"text": {"*": "text"}},
                }
            )
        )
    )
    text = Wikipedia(session).get_text("page")
    session.get.assert_called_once_with(
        "",
        params={
            "format": "json",
            "redirects": 1,
            "action": "parse",
            "prop": "text",
            "page": "page",
        },
    )
    assert text == "text"


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            dedent("""\
            <table>
              <tr>
                <td>0</td>
                <td>1</td>
              </tr>
            </table>",
        """),
            {
                0: ["0"],
                1: ["1"],
            },
        ),
        (
            dedent("""\
            <table>
              <tr>
                <th>a</th>
              </tr>
              <tr>
                <td>0</td>
              </tr>
              <tr>
                <td>1</td>
              </tr>
            </table>",
        """),
            {
                ("a",): ["0", "1"],
            },
        ),
        (
            dedent("""\
            <table>
              <tr>
                <th>a</th>
              </tr>
              <tr>
                <td>0</td>
              </tr>
              <tr>
                <th>a</th>
              </tr>
              <tr>
                <td>1</td>
              </tr>
            </table>",
        """),
            {
                ("a",): ["0", "1"],
            },
        ),
        (
            dedent("""\
            <table>
              <tr>
                <th colspan=2>a</th>
              </tr>
              <tr>
                <th>b</th>
                <th>c</th>
              </tr>
              <tr>
                <td>0</td>
                <td>1</td>
              </tr>
            </table>",
        """),
            {
                ("a", "b"): ["0"],
                ("a", "c"): ["1"],
            },
        ),
    ],
)
def test_parse_table(text, expected):
    """Parsing an HTML table should return a dictionary of values."""
    table = BeautifulSoup(text, "html.parser")
    result = parse_table(table)
    assert result == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", 0),
        ("<table></table>", 1),
        ("<table></table><table></table>", 2),
    ],
)
def test_parse_tables(text, expected):
    """Parsing HTML tables should return the same number of tables."""
    tables = parse_tables(text)
    assert len(tables) == expected


def test_get_companion_plants():
    """Getting companion plants should concatenate categories."""
    wikipedia = Mock(get_text=Mock(return_value=dedent("""\
        <table>
          <tr>
            <th colspan=2>Vegetables</th>
          </tr>
          <tr>
            <th>Common name</th>
            <th>Helps</th>
          </tr>
          <tr>
            <td>a</td>
            <td>x [1]</td>
          </tr>
        </table>
        <table>
          <tr>
            <th colspan=2>Fruits</th>
          </tr>
          <tr>
            <th>Common name</th>
            <th>Helps</th>
          </tr>
          <tr>
            <td>b</td>
            <td>y </td>
          </tr>
        </table>
        """)))
    df = get_companion_plants(wikipedia)
    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            {
                "Common name": ["a", "b"],
                "Helps": ["x", "y"],
                "Category": ["Vegetables", "Fruits"],
            },
        ),
    )
