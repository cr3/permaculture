"""Plants For A Future database."""

import logging
import re
from functools import partial

import xlrd
from attrs import define, field

from permaculture.database import DatabaseElement, DatabaseIterablePlugin
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
class PFAFModel:
    file: PFAFFile
    locales: Locales = field(factory=partial(Locales.from_domain, "pfaf"))

    @classmethod
    def from_cache_dir(cls, cache_dir):
        storage = FileStorage(cache_dir)
        file = PFAFFile(storage)
        return cls(file)

    def convert(self, key, value):
        def to_list(old_value):
            return [to_str(v) for v in re.findall("[A-Z][^A-Z]*", old_value)]

        def to_str(old_value):
            return self.locales.translate(old_value, key).lower()

        types = {
            "Deciduous/Evergreen": to_list,
            "Growth rate": to_list,
            "Moisture": to_list,
            "Shade": to_list,
            "Soil": to_list,
            "pH": to_list,
        }
        if isinstance(value, str):
            value = types.get(key, to_str)(value)
        return to_str(key), value

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
        ignore = {
            "Author",
            "Cultivation details",
            "Edible uses",
            "Known hazards",
            "Medicinal",
            "Propagation",
            "Uses notes",
        }
        for row in rows:
            yield dict(
                self.convert(k, v.value)
                for k, v in zip(header, row, strict=True)
                if k not in ignore
            )


@define(frozen=True)
class PFAFDatabase(DatabaseIterablePlugin):
    model: PFAFModel

    @classmethod
    def from_config(cls, config):
        model = PFAFModel.from_cache_dir(config.cache_dir)
        return cls(model)

    def iterate(self):
        for p in self.model.all_plants():
            yield DatabaseElement(
                "PFAF",
                p["scientific name"],
                [p["common name"]],
                p,
            )
