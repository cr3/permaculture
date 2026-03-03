"""Ingestor protocol for fetching plant data from remote sources."""

import re
from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from permaculture.database import DatabasePlant
from permaculture.registry import registry_load


@runtime_checkable
class Ingestor(Protocol):
    """Protocol for fetching plant data from a remote source."""

    @classmethod
    def from_config(cls, config): ...

    def fetch_all(self) -> Iterator[DatabasePlant]:
        """Yield all plants from this source."""
        ...


class Ingestors(dict):
    @classmethod
    def load(cls, config=None, registry=None):
        """Load ingestors from registry."""
        if registry is None or "ingestors" not in registry:
            registry = registry_load("ingestors", registry)

        include = re.compile("|".join(config.databases), re.I)
        ingestors = {
            k: v.from_config(config)
            for k, v in registry.get("ingestors", {}).items()
            if include.match(k)
        }

        return cls(ingestors)

    def select(self, names):
        """Select ingestors by name.

        Returns all ingestors when names is empty.
        Raises ValueError on unknown names.
        """
        if not names:
            return self

        unknown = set(names) - self.keys()
        if unknown:
            raise ValueError(
                f"unknown ingestor(s): {', '.join(sorted(unknown))}"
                f" (available: {', '.join(sorted(self))})"
            )

        return type(self)({k: v for k, v in self.items() if k in names})
