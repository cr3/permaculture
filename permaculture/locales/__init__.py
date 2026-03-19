"""Locales for naming conventions."""

import gettext
from pathlib import Path

from attrs import define, field

LOCALES_DIR = Path(__file__).parent


@define(frozen=True)
class Locales:
    translations: gettext.GNUTranslations = field()

    @classmethod
    def from_domain(
        cls,
        domain: str,
        locales_dir: Path = LOCALES_DIR,
        language: str = "en",
    ):
        translations = gettext.translation(
            domain,
            localedir=locales_dir,
            languages=[language],
        )
        return cls(translations)

    def translate(self, message: str, context: str = "") -> str:
        if not message:
            return message

        if context:
            new_message = self.translations.pgettext(context, message)
            if new_message != message:
                return new_message

        return self.translations.gettext(message)

    def translate_data(self, data, context=""):
        """Recursively translate dictionary keys and string values."""
        if not isinstance(data, dict):
            return data

        return {
            self.translate(key): (
                self.translate_data(value, context=key)
                if isinstance(value, dict)
                else [self.translate(item, context=key) for item in value]
                if isinstance(value, list)
                else self.translate(value, context=key)
                if isinstance(value, str)
                else value
            )
            for key, value in data.items()
        }
