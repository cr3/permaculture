"""Plants For A Future database."""

import logging

import xlrd
from attrs import define

from permaculture.database import DatabaseElement, DatabaseIterablePlugin
from permaculture.storage import FileStorage

logger = logging.getLogger(__name__)


@define(frozen=True)
class PFAF:
    storage: FileStorage

    @classmethod
    def from_cache_dir(cls, cache_dir):
        storage = FileStorage(cache_dir)
        return cls(storage)

    def main_database(self):
        path = self.storage.key_to_path("plants-for-a-future")
        wb = xlrd.open_workbook(path)
        return wb.sheet_by_name("MAIN DATABASE")


def apply_legend(row):
    legend = {
        "Deciduous/Evergreen": {
            "D": "Deciduous",
            "E": "Evergreen",
        },
        "pH": {
            "A": "Acid",
            "N": "Neutral",
            "B": "Base/Alkaline",
        },
        "Shade": {
            "F": "Full",
            "S": "Semi",
            "N": "None",
        },
        "Soil": {
            "L": "Light(sandy)",
            "M": "Medium(loam)",
            "H": "Heavy",
        },
    }
    for k, v in legend.items():
        if k in row:
            row[k] = [v.get(x, x) for x in row[k]]
        else:
            logger.warning("%(key)r not found in data", {"key": k})

    return row


def all_plants(pfaf):
    try:
        ws = pfaf.main_database()
    except FileNotFoundError:
        return []

    rows = ws.get_rows()
    header = [h.value for h in next(rows)]
    rows = (
        dict(zip(header, [c.value for c in cells], strict=True))
        for cells in rows
    )
    return [apply_legend(row) for row in rows]


@define(frozen=True)
class PFAFDatabase(DatabaseIterablePlugin):
    pfaf: PFAF

    @classmethod
    def from_config(cls, config):
        pfaf = PFAF.from_cache_dir(config.cache_dir)
        return cls(pfaf)

    def iterate(self):
        for p in all_plants(self.pfaf):
            yield DatabaseElement(
                "PFAF", p["Latin name"], [p["Common name"]], p
            )
