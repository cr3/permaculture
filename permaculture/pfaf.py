"""Plants for a future database."""

import logging

import xlrd
from attrs import define

from permaculture.iterator import IteratorElement
from permaculture.storage import FileStorage

logger = logging.getLogger(__name__)


@define(frozen=True)
class Pfaf:
    storage: FileStorage

    @classmethod
    def with_cache_dir(cls, cache_dir):
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
            logger.warn("%(key)r not found in data", {"key": k})

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


def iterator(cache_dir):
    pfaf = Pfaf.with_cache_dir(cache_dir)
    return [
        IteratorElement("PFAF", p["Latin name"], [p["Common name"]], p)
        for p in all_plants(pfaf)
    ]
