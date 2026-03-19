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


def test_locales_translate_data_non_dict():
    """Non-dict input should be returned as-is."""
    locales = Locales.from_domain("api", language="fr")
    assert locales.translate_data([1, 2, 3]) == [1, 2, 3]


def test_locales_translate_data_flat():
    """Translate data should translate top-level keys."""
    locales = Locales.from_domain("api", language="fr")
    data = {"scientific name": "test", "height": 1.2}
    result = locales.translate_data(data)
    assert result == {"nom scientifique": "test", "hauteur": 1.2}


def test_locales_translate_data_nested():
    """Translate data should recurse into nested dicts."""
    locales = Locales.from_domain("api", language="fr")
    data = {"height": {"max": 1.2}}
    result = locales.translate_data(data)
    assert result == {"hauteur": {"max": 1.2}}


def test_locales_translate_data_passthrough():
    """Untranslated keys should pass through unchanged."""
    locales = Locales.from_domain("api", language="fr")
    data = {"unknown key": 42}
    result = locales.translate_data(data)
    assert result == {"unknown key": 42}


def test_locales_translate_data_string_values():
    """Translate data should translate string values using context."""
    locales = Locales.from_domain("api", language="fr")
    data = {"growth rate": "fast"}
    result = locales.translate_data(data)
    assert result == {"taux de croissance": "rapide"}


def test_locales_translate_data_list_values():
    """Translate data should translate list items using context."""
    locales = Locales.from_domain("api", language="fr")
    data = {"sun": ["full", "partial"]}
    result = locales.translate_data(data)
    assert result == {"soleil": ["plein soleil", "mi-ombre"]}
