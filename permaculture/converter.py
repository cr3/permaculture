"""Converter base."""

import re
import string
from abc import ABC, abstractmethod
from itertools import chain

from attrs import define

from permaculture.locales import Locales

FLOAT_RE = r"([+-]?\d+(?:\.\d*)?)"


@define(frozen=True)
class Converter(ABC):
    @property
    @abstractmethod
    def locales(self) -> Locales:
        ...

    def translate(self, message, context=None):
        """Convenience function to translate from locales."""
        return self.locales.translate(message, context).lower()

    def convert_bool(self, key, value):
        if value in ("Y", "Yes"):
            return [(self.translate(key), True)]
        elif value in ("N", "No"):
            return [(self.translate(key), False)]
        else:
            raise ValueError(f"Unknown boolean: {value!r}")

    def convert_float(self, key, value, unit=1.0):
        if m := re.match(FLOAT_RE, value):
            new_value = float(m.group(1)) * unit
        elif value == "":
            new_value = None
        else:
            raise ValueError(f"Unknown float: {value!r}")

        return [(self.translate(key), new_value)]

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
        punctuation = re.escape(string.punctuation)
        new_value = [
            self.translate(v, key)
            for v in re.findall(rf"[^\s{punctuation}][a-z]*", value)
        ]
        return [(f"{k}/{v}", True) for v in new_value]

    def convert_list(self, key, value, sep=r",\s*"):
        """Convert a list of strings into a list of items.

        The strings can be separated by a comma, or whitespace, or both.
        """
        k = self.translate(key)
        new_value = [self.translate(v, key) for v in re.split(sep, value)]
        return [(f"{k}/{v}", True) for v in new_value]

    def convert_range(self, key, value, unit=1.0):
        k = self.translate(key)
        n = [
            float(i) * unit
            for i in re.findall(FLOAT_RE, value.replace(",", "."))
        ]
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

    def convert_item(self, key, value):
        return self.convert_string(key, value)

    def convert(self, data):
        return dict(
            chain.from_iterable(
                self.convert_item(k, v) for k, v in data.items()
            )
        )
