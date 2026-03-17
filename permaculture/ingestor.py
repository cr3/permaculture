"""Ingestor protocol for fetching plant data from remote sources."""

import logging
import re
from collections.abc import Iterator
from functools import wraps
from typing import Protocol, runtime_checkable

from permaculture.plant import IngestorPlant
from permaculture.registry import registry_load

logger = logging.getLogger(__name__)


@runtime_checkable
class Ingestor(Protocol):
    """Protocol for fetching plant data from a remote source."""

    name: str

    @classmethod
    def from_config(cls, config, name: str): ...

    def fetch_all(self) -> Iterator[IngestorPlant]:
        """Yield all plants from this source."""
        ...


def logged_fetch(method):
    """Decorator that wraps a fetch_all generator with progress logging."""
    @wraps(method)
    def wrapper(self):
        count = 0
        for plant in method(self):
            count += 1
            if count % 100 == 0:
                logger.info("%s: ingested %d plants", self.name, count)
            yield plant
        logger.info("%s: ingested %d plants total", self.name, count)
    return wrapper


class Ingestors(dict):
    @classmethod
    def load(cls, config=None, registry=None):
        """Load ingestors from registry."""
        if registry is None or "ingestors" not in registry:
            registry = registry_load("ingestors", registry)

        include = re.compile("|".join(config.ingestors), re.I)
        ingestors = {
            k: v.from_config(config, k)
            for k, v in registry.get("ingestors", {}).items()
            if include.match(k)
        }

        return cls(ingestors)
