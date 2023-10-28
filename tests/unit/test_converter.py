"""Unit tests for the converter module."""

import pytest

from permaculture.converter import Converter
from permaculture.locales import Locales


@pytest.fixture
def converter():
    """Return a testing Converter."""
    locales = Locales.from_domain("testing")
    return Converter(locales)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Yes", True),
        ("Y", True),
        ("No", False),
        ("N", False),
    ],
)
def test_converter_convert_bool(converter, value, expected):
    """Converting a boolean should parse Yes and No."""
    result = converter.convert_bool("", value)
    assert result == [("", expected)]


def test_converter_convert_bool_error(converter):
    """Converting an unknown boolean should raise."""
    with pytest.raises(ValueError):
        converter.convert_bool("", "test")


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("key", "1"),
            [("key", 1.0)],
            id="1",
        ),
        pytest.param(
            ("key", "+1"),
            [("key", 1.0)],
            id="+1",
        ),
        pytest.param(
            ("key", "-1"),
            [("key", -1.0)],
            id="-1",
        ),
        pytest.param(
            ("key", "1."),
            [("key", 1.0)],
            id="1.",
        ),
        pytest.param(
            ("key", "1.0"),
            [("key", 1.0)],
            id="1.0",
        ),
        pytest.param(
            ("key", ""),
            [],
            id="<empty>",
        ),
    ],
)
def test_converter_convert_float(converter, item, expected):
    """Converting a float should parse strings."""
    result = converter.convert_float(*item)
    assert result == expected


def test_converter_convert_float_unit(converter):
    """Converting a float should parse strings."""
    result = converter.convert_float("", "5.0", 2.0)
    assert result == [("", 10.0)]


def test_converter_convert_float_error(converter):
    """Converting an unknown float should raise."""
    with pytest.raises(ValueError):
        converter.convert_float("", "test")


def test_converter_convert_ignore(converter):
    """Converting an ignore item should return an empty list."""
    result = converter.convert_ignore("key", "value")
    assert result == []


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", 1),
        (1, 1),
    ],
)
def test_converter_convert_int(converter, value, expected):
    """Converting a int should parse strings and ints."""
    result = converter.convert_int("", value)
    assert result == [("", expected)]


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("key", "A"),
            [("key/a", True)],
            id="A",
        ),
        pytest.param(
            ("key", "AB"),
            [("key/a", True), ("key/b", True)],
            id="AB",
        ),
        pytest.param(
            ("key", "Ab"),
            [("key/ab", True)],
            id="Ab",
        ),
        pytest.param(
            ("key", "AbC"),
            [("key/ab", True), ("key/c", True)],
            id="AbC",
        ),
    ],
)
def test_converter_convert_letters(converter, item, expected):
    """Converting letters should split into each letter."""
    result = converter.convert_letters(*item)
    assert result == expected


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("key", "A"),
            [("key/a", True)],
            id="A",
        ),
        pytest.param(
            ("key", "A,B"),
            [("key/a", True), ("key/b", True)],
            id="A,B",
        ),
        pytest.param(
            ("key", "A, B"),
            [("key/a", True), ("key/b", True)],
            id="A, B",
        ),
    ],
)
def test_converter_convert_list(converter, item, expected):
    """Converting list should split into each letter."""
    result = converter.convert_list(*item)
    assert result == expected


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("key", "1 inches - 2 inches"),
            [
                ("key/min", 1),
                ("key/max", 2),
            ],
            id="unit",
        ),
        pytest.param(
            ("key", "1.0 - 2.0"),
            [
                ("key/min", 1.0),
                ("key/max", 2.0),
            ],
            id="dash",
        ),
        pytest.param(
            ("key", "1.0 \u2013 2.0"),
            [
                ("key/min", 1.0),
                ("key/max", 2.0),
            ],
            id="endash",
        ),
        pytest.param(
            ("key", "1.0"),
            [
                ("key/min", 1.0),
                ("key/max", 1.0),
            ],
            id="single value",
        ),
    ],
)
def test_converter_convert_range(converter, item, expected):
    """Converting a range should support single and double values."""
    result = converter.convert_range(*item)
    assert result == expected


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("key", "string"),
            [("key", "string")],
            id="string",
        ),
        pytest.param(
            ("key", 1),
            [("key", 1)],
            id="int",
        ),
    ],
)
def test_converter_convert_string(converter, item, expected):
    """Converting a string should not convert other types."""
    result = converter.convert_string(*item)
    assert result == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "key a.",
            "key",
        ),
        ("key (paren)", "key"),
    ],
)
def test_converter_convert_token(converter, value, expected):
    """Converting a token should normalize the value."""
    result = converter.convert_token("", value)
    assert result == [("", expected)]
