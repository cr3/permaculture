"""Unit tests for the wikipedia module."""

from textwrap import dedent
from unittest.mock import Mock

import pandas as pd

from permaculture.wikipedia import Wikipedia, get_companion_plants

from .stubs import StubRequestsResponse


def test_wikipedia_get():
    """The Wikipedia get method should GET with the given action."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    Wikipedia(client).get("test")
    client.get.assert_called_once_with(
        "",
        params={
            "format": "json",
            "redirects": 1,
            "action": "test",
        },
    )


def test_wikipedia_get_text():
    """The Wikipedia get text method should parse the page text."""
    client = Mock(
        get=Mock(
            return_value=StubRequestsResponse(
                json=lambda: {
                    "parse": {"text": {"*": "text"}},
                }
            )
        )
    )
    text = Wikipedia(client).get_text("page")
    client.get.assert_called_once_with(
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
