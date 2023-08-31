"""Unit tests for the Wikipedia companion module."""

from textwrap import dedent
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from permaculture.wikipedia.companion import get_companion_plants, main


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


@patch("sys.stdout")
def test_main_help(stdout):
    """The main function should output usage when asked for --help."""
    with pytest.raises(SystemExit):
        main(["--help"])

    stdout.write.call_args[0][0].startswith("usage")
