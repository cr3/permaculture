"""Design Ecologique database."""

import re
from csv import reader
from functools import partial
from io import StringIO
from itertools import chain

from attrs import define, field
from bs4 import BeautifulSoup
from requests import Session
from yarl import URL

from permaculture.database import DatabaseIterablePlugin, DatabasePlant
from permaculture.google import GoogleSpreadsheet
from permaculture.http import HTTPSession
from permaculture.locales import Locales
from permaculture.storage import Storage, null_storage


class DEPlant(DatabasePlant):
    @property
    def scientific_name(self):
        return f"{self['genus']} {self['species']}"

    @property
    def common_names(self):
        return list(filter(None, [self["common name"], self["french name"]]))


@define(frozen=True)
class DEWeb:
    """Design Ecologique web interface."""

    session: Session = field()
    storage: Storage = field(default=null_storage)

    def perenial_plants_list(self):
        """List of perenial plants useful for permaculture in Quebec.

        :returns: Google spreadsheet with plants.
        """
        response = self.session.get("/liste-de-plantes-vivaces/")
        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one("a[href*=spreadsheets]")
        if not element:
            raise KeyError("Link to Google spreadsheets not found")

        url = URL(element["href"])
        return GoogleSpreadsheet.from_url(url, self.storage)


@define(frozen=True)
class DEConverter:
    locales: Locales = field(factory=partial(Locales.from_domain, "de"))

    def translate(self, message, context=None):
        """Convenience function to translate from locales."""
        return self.locales.translate(message, context).lower()

    def convert_ignore(self, *_):
        return []

    def convert_list(self, key, value):
        new_value = [self.translate(v, key) for v in re.split(r",?\s+", value)]
        if len(new_value) == 1 and new_value[0] == value:
            new_value = [self.translate(v, key) for v in value]

        k = self.translate(key)
        return [(f"{k}/{v}", True) for v in new_value]

    def convert_range(self, key, value):
        k = self.translate(key)
        n = [float(i) for i in re.findall(r"[0-9.]+", value.replace(",", "."))]
        match len(n):
            case 2:
                return [(f"{k}/min", n[0]), (f"{k}/max", n[1])]
            case 1:
                return [(f"{k}/min", n[0]), (f"{k}/max", n[0])]
            case 0:
                return []
            case _:
                raise ValueError(f"Unsupported range: {value!r}")

    def convert_string(self, key, value):
        value = True if value == "X" else self.translate(value, key)
        return [(self.translate(key), value)]

    def convert_item(self, key, value):
        dispatchers = {
            "Accumulateur de Nutriments": self.convert_ignore,
            "Comestible": self.convert_list,
            "Couleur de feuillage": self.convert_list,
            "Couleur de floraison": self.convert_list,
            "Couvre-sol": self.convert_ignore,
            "Cultivars intéressants": self.convert_ignore,
            "Eau": self.convert_list,
            "Forme": self.convert_list,
            "Haie": self.convert_ignore,
            "Hauteur(m)": self.convert_range,
            "Inconvénient": self.convert_list,
            "Intérêt automnale hivernal": self.convert_ignore,
            "Largeur(m)": self.convert_range,
            "Lien Information": self.convert_ignore,
            "Lumière": self.convert_list,
            "Multiplication": self.convert_list,
            "Notes": self.convert_ignore,
            "Où peut-on la trouver?": self.convert_ignore,
            "Pollinisateurs": self.convert_list,
            "Période de floraison": self.convert_list,
            "Période de taille": self.convert_list,
            "Racine": self.convert_list,
            "Rythme de croissance": self.convert_list,
            "Texture du sol": self.convert_list,
            "Utilisation écologique": self.convert_list,
            "Vie sauvage": self.convert_list,
            "pH (Min-Max)": self.convert_range,
        }
        return dispatchers.get(key, self.convert_string)(key, value)

    def convert(self, data):
        return dict(
            chain.from_iterable(
                self.convert_item(k, v) for k, v in data.items()
            )
        )


@define(frozen=True)
class DEModel:
    web: DEWeb = field()
    converter: DEConverter = field(factory=DEConverter)

    @classmethod
    def from_url(cls, url: URL, storage=null_storage):
        """Instantiate a Design Ecologique model from URL."""
        session = HTTPSession(url).with_cache(storage)
        web = DEWeb(session, storage)
        return cls(web)

    def get_perenial_plants(self):
        data = self.web.perenial_plants_list().export(0)
        csv = reader(StringIO(data))
        next(csv)  # Skip groups
        header = [h.strip() for h in next(csv)]
        for row in csv:
            yield self.converter.convert(dict(zip(header, row, strict=True)))


@define(frozen=True)
class DEDatabase(DatabaseIterablePlugin):
    model: DEModel

    @classmethod
    def from_config(cls, config):
        model = DEModel.from_url(
            "https://designecologique.ca",
            config.storage,
        )
        return cls(model)

    def iterate(self):
        return map(DEPlant, self.model.get_perenial_plants())
