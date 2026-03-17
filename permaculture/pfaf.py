"""Plants For A Future database."""

import logging
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import ClassVar

import xlrd
from attrs import define, field

from permaculture.converter import Converter
from permaculture.ingestor import logged_fetch
from permaculture.locales import Locales
from permaculture.plant import IngestorPlant
from permaculture.priority import LocationPriority, Priority

PFAF_ORIGIN = "https://pfaf.org/"

logger = logging.getLogger(__name__)


@define(frozen=True)
class PFAFFile:
    path: Path

    def main_database(self):
        wb = xlrd.open_workbook(self.path)
        return wb.sheet_by_name("MAIN DATABASE")


@define(frozen=True)
class PFAFConverter(Converter):
    locales: Locales = field(factory=partial(Locales.from_domain, "pfaf"))

    def convert_float(self, key, value):
        if isinstance(value, float | int):
            return [(self.translate(key), float(value))]
        else:
            return super().convert_float(key, value)

    DISPATCH: ClassVar[dict[str, Callable]] = {
        "Author": Converter.convert_ignore,
        "Common name": Converter.convert_list,
        "Cultivation details": Converter.convert_ignore,
        "Deciduous/Evergreen": Converter.convert_letters,
        "Drought": Converter.convert_ignore,
        "Edible uses": Converter.convert_ignore,
        "Growth rate": Converter.convert_list,
        "Habitat": Converter.convert_ignore,
        "Height": convert_float,
        "Known hazards": Converter.convert_ignore,
        "Latin name": Converter.convert_token,
        "Medicinal": Converter.convert_ignore,
        "Moisture": Converter.convert_letters,
        "Pollinators": Converter.convert_list,
        "Propagation": Converter.convert_ignore,
        "Range": Converter.convert_ignore,
        "Shade": Converter.convert_letters,
        "Soil": Converter.convert_letters,
        "Uses notes": Converter.convert_ignore,
        "Width": convert_float,
        "Wildlife": Converter.convert_ignore,
        "pH": Converter.convert_letters,
    }


@define(frozen=True)
class PFAFModel:
    file: PFAFFile
    converter: PFAFConverter = field(factory=PFAFConverter)

    @classmethod
    def from_path(cls, path):
        file = PFAFFile(Path(path))
        return cls(file)

    def all_plants(self):
        try:
            ws = self.file.main_database()
        except FileNotFoundError as error:
            logger.info("Skipping Plants For A Future: %(error)s", {"error": error})
            return []

        rows = ws.get_rows()
        header = [h.value for h in next(rows)]
        for row in rows:
            yield self.converter.convert(
                {k: v.value for k, v in zip(header, row, strict=True)}
            )


@define(frozen=True)
class PFAFIngestor:
    name: str
    model: PFAFModel
    title: str = "Plants For A Future"
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config, name):
        """Instantiate PFAFIngestor from config."""
        model = PFAFModel.from_path(config.pfaf_file)
        priority = LocationPriority("United Kingdom").with_cache(config.storage)
        return cls(name, model=model, priority=priority)

    @logged_fetch
    def fetch_all(self):
        for p in self.model.all_plants():
            yield IngestorPlant(
                p, self.priority.weight,
                ingestor=self.name, title=self.title, source=PFAF_ORIGIN,
            )
