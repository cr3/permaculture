"""Design Ecologique database."""

import logging
import re
from csv import reader
from io import StringIO

from attrs import define, field
from bs4 import BeautifulSoup
from yarl import URL

from permaculture.google import GoogleSpreadsheet
from permaculture.http import HTTPClient
from permaculture.iterator import IteratorElement

logger = logging.getLogger(__name__)


@define(frozen=True)
class DesignEcologique:
    """Design Ecologique web interface."""

    client: HTTPClient = field()
    _cache_dir = field(default=None)

    @classmethod
    def from_url(cls, url: URL, cache_dir=None):
        """Instantiate Design Ecologique from URL."""
        client = HTTPClient.with_cache_all(url, cache_dir)
        return cls(client, cache_dir)

    def perenial_plants(self):
        response = self.client.get("/liste-de-plantes-vivaces/")
        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one("a[href*=spreadsheets]")
        if not element:
            raise KeyError("Link to Google spreadsheets not found")

        url = URL(element["href"])
        return GoogleSpreadsheet.from_url(url, self._cache_dir)


def apply_legend(row):
    legend = {
        "Comestible": {
            "Fl": "Fleur",
            "Fr": "Fruit",
            "Fe": "Feuille",
            "N": "Noix",
            "G": "Graine",
            "R": "Racine",
            "S": "Sève",
            "JP": "Jeune pousse",
            "T": "Tige",
            "B": "Bulbe",
        },
        "Couleur de floraison": {
            "Rg": "Rouge",
            "Rs": "Rose",
            "B": "Blanc",
            "J": "Jaune",
            "O": "Orangé",
            "P": "Pourpre",
            "V": "Verte",
            "Br": "Brun",
            "Bl": "Bleu",
        },
        "Couleur de feuillage": {
            "V": "Vert",
            "Po": "Pourpre",
            "Pa": "Panaché",
            "P": "Pale",
            "F": "Foncé",
            "T": "Tacheté",
            "J": "Jaune",
        },
        "Eau": {
            "▁": "Peu",
            "▅": "Moyen",
            "█": "Beaucoup",
        },
        "Forme": {
            "A": "Arbre",
            "Ar": "Arbuste",
            "H": "Herbacée",
            "G": "Grimpante",
        },
        "Inconvénient": {
            "E": "Expansif",
            "D": "Dispersif",
            "A": "Allergène",
            "P": "Poison",
            "Épi": "Épineux",
            "V": "Vigne vigoureuse",
            "B": "Brûlure",
            "G": "Grimpant invasif",
            "Pe": "Persistant",
        },
        "Intérêt automnale hivernal": {
            "A": "Automne",
            "H": "Hivernale",
        },
        "Lumière": {
            "○": "Plein soleil",
            "◐": "Mi-Ombre",
            "●": "Ombre",
        },
        "Multiplication": {
            "B": "Bouturage",
            "M": "Marcottage",
            "D": "Division",
            "S": "Semi",
            "G": "Greffe",
            "St": "Stolon",
            "P": "Printemps",
            "A": "Automne",
            "É": "Été",
            "T": "Tubercule",
        },
        "Période de floraison": {
            "P": "Printemps",
            "É": "Été",
            "A": "Automne",
        },
        "Période de taille": {
            "AD": "Avant le débourement",
            "AF": "Après la floraison",
            "P": "Printemps",
            "É": "Été",
            "A": "Automne",
            "T": "en tout temps",
            "N": "Ne pas tailler",
        },
        "Pollinisateurs": {
            "S": "Spécialistes",
            "G": "Généralistes",
            "V": "Vent",
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
        "Rythme de croissance": {
            "R": "Rapide",
            "M": "Moyen",
            "L": "Lent",
        },
        "Texture du sol": {
            "░": "Léger",
            "▒": "Moyen",
            "▓": "Lourd",
            "O": "Aquatique",
        },
        "Utilisation écologique": {
            "BR": "Bande Riveraine",
            "P": "Pentes",
            "Z": "Zone innondable",
        },
        "Vie sauvage": {
            "N": "Nourriture",
            "A": "Abris",
            "NA": "Nourriture et Abris",
        },
    }
    for k, v in legend.items():
        if k in row:
            old_value = row[k]
            new_value = [v.get(x, x) for x in re.split(r",?\s+", old_value)]
            if len(new_value) == 1 and new_value[0] == old_value:
                new_value = [v.get(x, x) for x in old_value]

            row[k] = new_value
        else:
            logger.warn("%(key)r not found in data", {"key": k})

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
            "DE",
            f"{p['Genre']} {p['Espèce']}",
            [p["Nom Anglais"], p["Nom français"]],
            p,
        )
        for p in all_perenial_plants(de)
    ]
