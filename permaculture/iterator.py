"""Iterator utilities."""

import re
from collections.abc import Callable
from typing import Any

from attrs import define, field

from permaculture.registry import registry_load
from permaculture.tokenizer import tokenize


class IteratorElementNotFound(Exception):
    """Raised when an iterator element is not found."""


@define(frozen=True)
class IteratorElement:
    database: str = field()
    scientific_name: str = field(converter=tokenize)
    common_names: list[str] = field(converter=lambda x: list(filter(None, x)))
    characteristics: dict[str, Any] = field()


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
        for element in self.iterate():
            if any(
                re.search(name, tokenize(n), re.I)
                for n in element.common_names
            ):
                yield element

    def lookup(self, name):
        not_found = True
        for element in self.iterate():
            if re.match(name, element.scientific_name, re.I):
                not_found = False
                yield element

        if not_found:
            raise IteratorElementNotFound(name)
