"""Unit tests for the nlp module."""

import pytest

from permaculture.nlp import normalize


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param("foo", "foo", id="one word"),
        pytest.param("foô", "foo", id="accents"),
        pytest.param(" foo", "foo", id="leading space"),
        pytest.param("foo ", "foo", id="trailing space"),
        pytest.param("foo bar", "foo bar", id="two words"),
        pytest.param("foo  bar", "foo bar", id="space between"),
        pytest.param("foo x bar", "foo bar", id="single letter"),
        pytest.param("foo 012 bar", "foo bar", id="digits"),
        pytest.param("foo () baz", "foo baz", id="empty parenthesis"),
        pytest.param("foo (bar) baz", "foo baz", id="one set of parentheses"),
        pytest.param("(foo) bar (baz)", "bar", id="two sets of parentheses"),
        pytest.param("foo [] baz", "foo baz", id="empty brackets"),
        pytest.param("foo [bar] baz", "foo baz", id="one set of brackets"),
        pytest.param("[foo] bar [baz]", "bar", id="two sets of brackets"),
        pytest.param("FOO", "foo", id="lower case"),
        pytest.param("-foo-bar-", "foo bar", id="dash"),
        pytest.param(".foo..bar.", "foo bar", id="dot"),
    ],
)
def test_normalize(text, expected):
    """Normalizing text should return the expected result."""
    result = normalize(text)
    assert result == expected
