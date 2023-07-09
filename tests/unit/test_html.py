"""Unit tests for the html module."""

from textwrap import dedent

import pytest
from bs4 import BeautifulSoup

from permaculture.html import (
    parse_table,
    parse_tables,
)


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
    table = BeautifulSoup(text)
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
