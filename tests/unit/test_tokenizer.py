"""Unit tests for the tokenizer module."""

import pytest

from permaculture.tokenizer import tokenize


@pytest.mark.parametrize(
    "words, expected",
    [
        pytest.param("foo", "foo", id="one word"),
        pytest.param("foô", "foo", id="accents"),
        pytest.param(" foo", "foo", id="leading space"),
        pytest.param("foo ", "foo", id="trailing space"),
        pytest.param("foo bar", "foo bar", id="two words"),
        pytest.param("foo  bar", "foo bar", id="space between"),
        pytest.param("foo x bar", "foo bar", id="single letter"),
        pytest.param("FOO", "foo", id="lower case"),
    ],
)
def test_tokenize(words, expected):
    """Tokenizing words should return the expected result."""
    result = tokenize(words)
    assert result == expected