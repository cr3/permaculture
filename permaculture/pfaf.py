"""Plants For A Future database."""

import logging
from functools import partial

import xlrd
from attrs import define, field

from permaculture.converter import Converter
from permaculture.database import DatabaseIterablePlugin, DatabasePlant
from permaculture.locales import Locales
from permaculture.storage import FileStorage

logger = logging.getLogger(__name__)


@define(frozen=True)
class PFAFFile:
    storage: FileStorage

    def main_database(self):
        path = self.storage.key_to_path("plants-for-a-future")
        wb = xlrd.open_workbook(path)
        return wb.sheet_by_name("MAIN DATABASE")


@define(frozen=True)
class PFAFConverter(Converter):
    locales: Locales = field(factory=partial(Locales.from_domain, "pfaf"))

    def convert_item(self, key, value):
        dispatchers = {
            "Author": self.convert_ignore,
            "Cultivation details": self.convert_ignore,
            "Deciduous/Evergreen": self.convert_letters,
            "Drought": self.convert_ignore,
            "Edible uses": self.convert_ignore,
            "Growth rate": self.convert_letters,
            "Known hazards": self.convert_ignore,
            "Medicinal": self.convert_ignore,
            "Moisture": self.convert_letters,
            "Propagation": self.convert_ignore,
            "Range": self.convert_ignore,
            "Shade": self.convert_letters,
            "Soil": self.convert_letters,
            "Uses notes": self.convert_ignore,
            "pH": self.convert_letters,
        }
        return dispatchers.get(key, self.convert_string)(key, value)


@define(frozen=True)
class PFAFModel:
    file: PFAFFile
    converter: PFAFConverter = field(factory=PFAFConverter)

    @classmethod
    def from_storage(cls, storage):
        file = PFAFFile(storage)
        return cls(file)

    def all_plants(self):
        try:
            ws = self.file.main_database()
        except FileNotFoundError as error:
            logger.debug(
                "Skipping Plants For A Future: %(error)s", {"error": error}
            )
            return []

        rows = ws.get_rows()
        header = [h.value for h in next(rows)]
        for row in rows:
            yield self.converter.convert(
                {k: v.value for k, v in zip(header, row, strict=True)}
            )


@define(frozen=True)
class PFAFDatabase(DatabaseIterablePlugin):
    model: PFAFModel

    @classmethod
    def from_config(cls, config):
        model = PFAFModel.from_storage(config.storage)
        return cls(model)

    def iterate(self):
        return map(DatabasePlant, self.model.all_plants())
