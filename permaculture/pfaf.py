"""Plants For A Future database."""

import logging
import re
from collections import defaultdict
from functools import partial
from itertools import chain

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
class PFAFConverter:
    locales: Locales = field(factory=partial(Locales.from_domain, "pfaf"))

    def translate(self, message, context=None):
        """Convenience function to translate from locales."""
        return self.locales.translate(message, context).lower()

    def convert_ignore(self, *_):
        return []

    def convert_list(self, key, value):
        k = self.translate(key)
        new_value = [
            self.translate(v, key) for v in re.findall("[A-Z][^A-Z]*", value)
        ]
        return [(f"{k}/{v}", True) for v in new_value]

    def convert_string(self, key, value):
        return [(self.translate(key), value)]

    def convert_item(self, key, value):
        dispatchers = defaultdict(
            lambda: self.convert_string,
            {
                "Author": self.convert_ignore,
                "Cultivation details": self.convert_ignore,
                "Deciduous/Evergreen": self.convert_list,
                "Edible uses": self.convert_ignore,
                "Growth rate": self.convert_list,
                "Known hazards": self.convert_ignore,
                "Medicinal": self.convert_ignore,
                "Moisture": self.convert_list,
                "Propagation": self.convert_ignore,
                "Shade": self.convert_list,
                "Soil": self.convert_list,
                "Uses notes": self.convert_ignore,
                "pH": self.convert_list,
            },
        )
        return dispatchers[key](key, value)

    def convert(self, data):
        return dict(
            chain.from_iterable(
                self.convert_item(k, v) for k, v in data.items()
            )
        )


@define(frozen=True)
class PFAFModel:
    file: PFAFFile
    converter: PFAFConverter = field(factory=PFAFConverter)

    @classmethod
    def from_cache_dir(cls, cache_dir):
        storage = FileStorage(cache_dir)
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
