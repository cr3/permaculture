"""Converter base."""

import re
import string
from collections.abc import Callable
from typing import ClassVar

from attrs import define, field

from permaculture.locales import Locales
from permaculture.nlp import normalize

FLOAT_RE = r"([+-]?\d+(?:\.\d*)?)"
LETTERS_RE = re.compile(rf"[^\s{re.escape(string.punctuation)}][a-z]*")


@define(frozen=True)
class Converter:
    locales: Locales = field()

    DISPATCH: ClassVar[dict[str, Callable]] = {}

    def translate(self, message, context=None):
        """Convenience function to translate from locales."""
        return self.locales.translate(message, context).lower()

    def convert_bool(self, key, value):
        if value in ("Y", "Yes", "TRUE"):
            return [(self.translate(key), True)]
        elif value in ("N", "No", "FALSE"):
            return [(self.translate(key), False)]
        else:
            raise ValueError(f"Unknown boolean: {value!r}")

    def convert_float(self, key, value, unit=1.0):
        if m := re.match(FLOAT_RE, value):
            f = float(m.group(1)) * unit
            return [(self.translate(key), f)]
        elif value == "":
            return []
        else:
            raise ValueError(f"Unknown float: {value!r}")

    def convert_ignore(self, *_):
        return []

    def convert_int(self, key, value):
        return [(self.translate(key), int(value))]

    def convert_letters(self, key, value):
        """Convert letters into a list of items.

        The letters can be any unicode character and they can be
        followed by lowercase letters. The list might not be separated
        by punctuation or whitespace.
        """
        k = self.translate(key)
        values = [
            self.translate(v, key)
            for v in LETTERS_RE.findall(value)
        ]
        return [(f"{k}/{v}", True) for v in values]

    def convert_list(self, key, value, sep=r",\s*"):
        """Convert a list of strings into a list of items.

        The strings are separated by a comma optionally followed by whitespace.
        """
        k = self.translate(key)
        values = [self.translate(v, key) for v in re.split(sep, value)]
        return [(f"{k}/{v}", True) for v in values if v is not None]

    def convert_range(self, key, value, unit=1.0):
        k = self.translate(key)
        n = [float(i) * unit for i in re.findall(FLOAT_RE, value)]
        match len(n):
            case 0:
                return []
            case 1:
                return [(f"{k}/min", n[0]), (f"{k}/max", n[0])]
            case _:
                return [(f"{k}/min", n[0]), (f"{k}/max", n[1])]

    def convert_string(self, key, value):
        if isinstance(value, str):
            value = self.translate(value, key)
        return [(self.translate(key), value)]

    def convert_token(self, key, value):
        return [(self.translate(key), normalize(value))]

    def convert_item(self, key, value):
        method = self.DISPATCH.get(key)
        if method is None:
            return self.convert_string(key, value)
        return method(self, key, value)

    def convert(self, data):
        return {
            k: v
            for item in data.items()
            if item[1] is not None and item[1] != ""
            for k, v in self.convert_item(*item)
        }
