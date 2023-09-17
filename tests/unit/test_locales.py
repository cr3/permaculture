"""Unit tests for the locales module."""

import pytest

from permaculture.locales import Locales


@pytest.mark.parametrize(
    "message, context, expected",
    [
        ("", None, ""),
        ("", "Context", ""),
        ("Test", None, "test without context"),
        ("Test", "Context", "test with context"),
        ("Foo", None, "Foo"),
        ("Foo", "Context", "Foo"),
    ],
)
def test_locales_translate(message, context, expected):
    """Translating a message with context should return the expected string."""
    locales = Locales.from_domain("testing")
    result = locales.translate(message, context)
    assert result == expected
