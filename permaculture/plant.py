"""Plant data classes."""

from collections.abc import Mapping

from attrs import define, field


@define(frozen=True, hash=False)
class Plant(Mapping):
    """Base for plant records with data mapping and weight."""

    data: dict
    weight: float

    @property
    def scientific_name(self):
        return self.data.get("scientific name", "")

    @property
    def common_names(self):
        return [
            key.removeprefix("common name/")
            for key in self.data
            if key.startswith("common name/")
        ]

    @property
    def names(self):
        return [self.scientific_name, *self.common_names]

    def __getitem__(self, key):
        return self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


@define(frozen=True, hash=False)
class IngestorPlant(Plant):
    """Plant record from a single ingestor."""

    ingestor: str = field(kw_only=True)
    title: str = field(kw_only=True)
    source: str = field(kw_only=True)


@define(frozen=True, hash=False)
class DatabasePlant(Plant):
    """Plant record merged from multiple ingestors."""

    ingestors: dict = field(kw_only=True)
    sources: dict = field(kw_only=True)
