"""Design Ecologique web interface."""

from csv import reader
from io import StringIO

from attrs import define
from bs4 import BeautifulSoup
from yarl import URL

from permaculture.google.spreadsheets import GoogleSpreadsheet
from permaculture.http import HTTPClient
from permaculture.iterator import IteratorElement


@define(frozen=True)
class DesignEcologique:
    """Design Ecologique web interface."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url, cache_dir=None):
        """Instantiate Design Ecologique from URL."""
        client = HTTPClient.with_cache_all(url, cache_dir)
        return cls(client)

    def perenial_plants(self):
        response = self.client.get("liste-de-plantes-vivaces")
        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one("a[href*=spreadsheets]")
        if not element:
            raise KeyError("Link to Google spreadsheets not found")

        url = URL(element["href"])
        return GoogleSpreadsheet.from_url(url)


def apply_legend(row):
    legend = {
        "Texture du sol": {
            "░": "Léger",
            "▒": "Moyen",
            "▓": "Lourd",
            "O": "Aquatique",
        },
        "Lumière": {
            "○": "Plein soleil",
            "◐": "Mi-Ombre",
            "●": "Ombre",
        },
        "Forme": {
            "A": "Arbre",
            "Ar": "Arbuste",
            "H": "Herbacée",
            "G": "Grimpante",
        },
        "Racine": {
            "B": "Bulbe",
            "C": "Charnu",
            "D": "Drageonnante",
            "F": "Faciculé",
            "L": "Latérales",
            "P": "Pivotante",
            "R": "Rhizome",
            "S": "Superficiel",
            "T": "Tubercule",
        },
        "Vie sauvage": {
            "N": "Nourriture",
            "A": "Abris",
            "NA": "Nourriture et Abris",
        },
    }
    for k, v in legend.items():
        if k in row:
            row[k] = " ".join(v.get(x, x) for x in row[k].split())

    return row


def all_perenial_plants(de):
    data = de.perenial_plants().export(0)
    csv = reader(StringIO(data))
    next(csv)  # Skip groups
    header = [h.strip() for h in next(csv)]
    rows = (dict(zip(header, plant, strict=True)) for plant in csv)
    return [apply_legend(row) for row in rows]


def iterator(cache_dir):
    de = DesignEcologique.from_url(
        "https://designecologique.ca",
        cache_dir,
    )
    return [
        IteratorElement(
            f"{p['Genre']} {p['Espèce']}",
            [p["Nom Anglais"], p["Nom français"]],
            p,
        )
        for p in all_perenial_plants(de)
    ]
