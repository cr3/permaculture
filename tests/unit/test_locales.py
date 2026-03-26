"""Unit tests for the locales module."""

import pytest

from permaculture.locales import (
    Locales,
    all_aliases,
)


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


def test_locales_translate_data_non_dict():
    """Non-dict input should be returned as-is."""
    locales = Locales.from_domain("de", language="fr")
    assert locales.translate_data([1, 2, 3]) == [1, 2, 3]


def test_locales_translate_data_flat():
    """Translate data should translate top-level keys."""
    locales = Locales.from_domain("de", language="fr")
    data = {"Largeur (m)": 1.2}
    result = locales.translate_data(data)
    assert result == {"spread": 1.2}


def test_locales_translate_data_nested():
    """Translate data should recurse into nested dicts."""
    locales = Locales.from_domain("de", language="fr")
    data = {"Hauteur (m)": {"max": 1.2}}
    result = locales.translate_data(data)
    assert result == {"height": {"max": 1.2}}


def test_locales_translate_data_passthrough():
    """Untranslated keys should pass through unchanged."""
    locales = Locales.from_domain("de", language="fr")
    data = {"unknown key": 42}
    result = locales.translate_data(data)
    assert result == {"unknown key": 42}


def test_locales_translate_data_string_values():
    """Translate data should translate string values using context."""
    locales = Locales.from_domain("de", language="fr")
    data = {"Comestible": "Fl"}
    result = locales.translate_data(data)
    assert result == {"edible uses": "flower"}


def test_locales_translate_data_list_values():
    """Translate data should translate list items using context."""
    locales = Locales.from_domain("de", language="fr")
    data = {"Comestible": ["Fl", "Fr"]}
    result = locales.translate_data(data)
    assert result == {"edible uses": ["flower", "fruit"]}


def test_all_aliases():
    """Aliases should include all languages by default."""
    aliases = all_aliases()
    assert "Hauteur (m)" in aliases["height"]
