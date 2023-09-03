"""Iterator utilities."""

import re
from collections.abc import Callable
from typing import Any

from attrs import define
from unidecode import unidecode

from permaculture.registry import registry_load


class IteratorElementNotFound(Exception):
    """Raised when an iterator element is not found."""


@define(frozen=True)
class IteratorElement:
    scientific_name: str
    common_names: list[str]
    characteristics: dict[str, Any]


IteratorPlugin = Callable[[str], list[IteratorElement]]


@define(frozen=True)
class Iterator:
    cache_dir: str | None
    _iterators: dict[str, IteratorPlugin]

    @classmethod
    def load(cls, cache_dir=None, registry=None):
        """Load iterators from registry."""
        if registry is None or "iterators" not in registry:
            registry = registry_load("iterators", registry)

        iterators = registry.get("iterators", {})

        return cls(cache_dir, iterators)

    def iterate(self):
        for iterate in self._iterators.values():
            yield from iterate(self.cache_dir)

    def search(self, name):
        return [
            element
            for element in self.iterate()
            if any(
                re.search(name, unidecode(n), re.I)
                for n in element.common_names
            )
        ]

    def lookup(self, name):
        characteristics = {}
        for iterate in self._iterators.values():
            iterate(self.cache_dir)
            for element in iterate(self.cache_dir):
                if re.match(name, element.scientific_name, re.I):
                    characteristics.update(element.characteristics)

        if not characteristics:
            raise IteratorElementNotFound(name)

        return characteristics
