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

    def field_translations(self):
        """Yield (msgid, msgstr) pairs for non-contextual entries."""
        for key, value in self.translations._catalog.items():
            if key and "\x04" not in key and value:
                yield key, value

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


def all_aliases(locales_dir: Path = LOCALES_DIR) -> dict[str, list[str]]:
    """Return a mapping from DB keys to their source name aliases.

    Scans all ingestor .mo files in the ``en`` locale and inverts
    the msgid → msgstr mapping so callers can discover that e.g.
    ``"Hauteur (m)"`` and ``"Height"`` are both aliases for ``"height"``.
    """
    result: dict[str, set] = {}
    en_dir = locales_dir / "en" / "LC_MESSAGES"
    for mo_path in en_dir.glob("*.mo"):
        domain = mo_path.stem
        locales = Locales.from_domain(domain, locales_dir)
        for msgid, msgstr in locales.field_translations():
            if msgstr != msgid:
                result.setdefault(msgstr, set()).add(msgid)
    return {k: sorted(v) for k, v in result.items()}
