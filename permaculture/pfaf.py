"""Plants For A Future database."""

import logging
from functools import partial
from pathlib import Path

import xlrd
from attrs import define, field

from permaculture.converter import Converter
from permaculture.plant import IngestorPlant
from permaculture.locales import Locales
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

    DISPATCH = {
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
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config, name):
        """Instantiate PFAFIngestor from config."""
        model = PFAFModel.from_path(config.pfaf_file)
        priority = LocationPriority("United Kingdom").with_cache(config.storage)
        return cls(name, model, priority)

    def fetch_all(self):
        count = 0
        for p in self.model.all_plants():
            count += 1
            if count % 100 == 0:
                logger.info("PFAF: ingested %d plants", count)
            yield IngestorPlant(
                p, self.priority.weight,
                ingestor=self.name, source=PFAF_ORIGIN,
            )
        logger.info("PFAF: ingested %d plants total", count)
