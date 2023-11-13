"""Unit tests for the nlp module."""

from argparse import ArgumentTypeError

import pytest

from permaculture.nlp import Extractor, normalize, score, score_type


def scorer(a, b):
    """Normalize the distance between 0 and 1 for two letters."""
    return 1 - abs(ord(a) - ord(b)) / 26


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


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("a", "a", 1.0),
        ("ab", "ab", 1.0),
        ("a a", "a a", 1.0),
        ("a b", "a b", 1.0),
        ("a b", "b a", 1.0),
        ("a", "b", 0.0),
    ],
)
def test_score(a, b, expected):
    """Scoring two strings should return the Levenshtein distance."""
    result = score(a, b)
    assert result == expected


@pytest.mark.parametrize(
    "score, expected",
    [
        ("0", 0.0),
        ("0.5", 0.5),
        ("1.0", 1.0),
    ],
)
def test_score_type(score, expected):
    """A valid score type should return a float."""
    result = score_type(score)
    assert result == expected


@pytest.mark.parametrize(
    "score",
    [
        "a",
        "2",
        "-1",
    ],
)
def test_score_type_error(score):
    """An invalid score type should raise."""
    with pytest.raises(ArgumentTypeError):
        score_type(score)


@pytest.mark.parametrize(
    "query, choices, expected",
    [
        ("a", [], []),
        ("a", ["a", "b"], [(1, "a"), (1, "b")]),
    ],
)
def test_extractor_extract(query, choices, expected):
    """Extracting should return the scores for each choice."""
    result = Extractor(query).extract(choices)
    assert list(result) == expected


@pytest.mark.parametrize(
    "query, choices, expected",
    [
        ("a", ["a", "b"], (1, "a")),
        ("b", ["a", "b"], (1, "b")),
    ],
)
def test_extractor_extract_one(query, choices, expected):
    """Extracting one should return the choice with the best score."""
    result = Extractor(query, scorer=scorer).extract_one(choices)
    assert result == expected


def test_extractor_extract_one_error():
    """Extracting one result from empty choices should raise."""
    with pytest.raises(ValueError):
        Extractor("a").extract_one([])


@pytest.mark.parametrize(
    "query, choices, expected",
    [
        ("a", ["a", "b"], "a"),
        ("b", ["a", "b"], "b"),
        ("a", ["b", "c"], "b"),
    ],
)
def test_extractor_choose(query, choices, expected):
    """Extract the choice with the best score."""
    result = Extractor(query, scorer=scorer).choose(choices)
    assert result == expected


def test_extractor_choose_error():
    """Extract a choice from empty choices should raise."""
    with pytest.raises(ValueError):
        Extractor("a").choose([])
