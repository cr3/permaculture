"""Local JSON file ingestor for plant data."""

import json
import logging
from pathlib import Path

from attrs import define, field

from permaculture.ingestor import logged_fetch
from permaculture.plant import IngestorPlant
from permaculture.priority import Priority

logger = logging.getLogger(__name__)


@define(frozen=True)
class LocalIngestor:
    """Ingest plants from a local JSON file."""

    name: str
    title: str = "Local"
    path: Path | None = None
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config, name):
        """Create a JSONIngestor from permaculture config."""
        path = getattr(config, "local_path", None)
        return cls(name, path=Path(path) if path else None)

    @logged_fetch
    def fetch_all(self):
        """Yield all plants from the JSON file."""
        if self.path is None:
            logger.debug("local: path not set, skipping")
            return

        data = json.loads(self.path.read_text())
        for plant in data:
            yield IngestorPlant(
                plant,
                self.priority.weight,
                ingestor=self.name,
                title=self.title,
                source=str(self.path),
            )
