"""Design Ecologique database."""

import re
import string
from csv import reader
from functools import partial
from io import StringIO

from attrs import define, evolve, field
from bs4 import BeautifulSoup
from yarl import URL

from permaculture.converter import Converter
from permaculture.database import Database, DatabasePlant
from permaculture.google import GoogleSpreadsheet
from permaculture.http import HTTPSession
from permaculture.locales import Locales
from permaculture.priority import LocationPriority, Priority
from permaculture.storage import Storage, null_storage

DE_ORIGIN = "https://designecologique.ca"


@define(frozen=True)
class DEWeb:
    """Design Ecologique web interface."""

    session: HTTPSession = field(factory=partial(HTTPSession, DE_ORIGIN))
    storage: Storage = field(default=null_storage)

    def with_cache(self, storage):
        session = self.session.with_cache(storage)
        return evolve(self, session=session, storage=storage)

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
class DEConverter(Converter):
    locales: Locales = field(factory=partial(Locales.from_domain, "de"))

    def translate(self, message, context=None):
        """Translate `*` to None."""
        return None if message == "*" else super().translate(message, context)

    def convert_bool(self, key, value):
        """Convert `X` to True, `*` to False, otherwise None."""
        new_value = True if value == "X" else False if value == "*" else None
        return [(self.translate(key), new_value)]

    def convert_period(self, key, value):
        punctuation = re.escape(string.punctuation)
        if values := [
            self.translate(v, key)
            for v in re.findall(rf"[^\s{punctuation}][a-z]*", value)
        ]:
            k = self.translate(key)
            return [(f"{k}/min", values[0]), (f"{k}/max", values[-1])]
        else:
            return []

    def convert_range(self, key, value, unit=1.0):
        return super().convert_range(key, value.replace(",", "."))

    def convert_item(self, key, value):
        dispatchers = {
            "Accumulateur de Nutriments": self.convert_ignore,
            "Comestible": self.convert_list,
            "Couleur de feuillage": self.convert_letters,
            "Couleur de floraison": self.convert_letters,
            "Couvre-sol": self.convert_ignore,
            "Cultivars intéressants": self.convert_ignore,
            "Eau": self.convert_letters,
            "Forme": self.convert_letters,
            "Fixateur Azote": self.convert_ignore,
            "Haie": self.convert_ignore,
            "Hauteur(m)": self.convert_range,
            "Inconvénient": self.convert_letters,
            "Intérêt automnale hivernal": self.convert_ignore,
            "Largeur(m)": self.convert_range,
            "Lien Information": self.convert_ignore,
            "Lumière": self.convert_letters,
            "Medicinal": self.convert_bool,
            "Multiplication": self.convert_letters,
            "Notes": self.convert_ignore,
            "Où peut-on la trouver?": self.convert_ignore,
            "Pollinisateurs": self.convert_letters,
            "Période de floraison": self.convert_period,
            "Période de taille": self.convert_list,
            "Racine": self.convert_letters,
            "Rythme de croissance": self.convert_letters,
            "Texture du sol": self.convert_letters,
            "Utilisation écologique": self.convert_list,
            "Vie sauvage": self.convert_letters,
            "pH (Min-Max)": self.convert_range,
        }
        return dispatchers.get(key, self.convert_string)(key, value)


@define(frozen=True)
class DEModel:
    web: DEWeb = field(factory=DEWeb)
    converter: DEConverter = field(factory=DEConverter)

    def with_cache(self, storage):
        web = self.web.with_cache(storage)
        return evolve(self, web=web)

    def get_perenial_plants(self):
        data = self.web.perenial_plants_list().export(0)
        csv = reader(StringIO(data))
        next(csv)  # Skip groups
        header = [h.strip() for h in next(csv)]
        for row in csv:
            yield self.converter.convert(dict(zip(header, row, strict=True)))


@define(frozen=True)
class DEDatabase(Database):
    model: DEModel = field(factory=DEModel)
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config):
        """Instantiate DEDatabase from config."""
        model = DEModel().with_cache(config.storage)
        priority = LocationPriority("Quebec").with_cache(config.storage)
        return cls(model, priority)

    def iterate(self):
        return (
            DatabasePlant(
                {
                    "scientific name": f"{p.pop('genus')} {p.pop('species')}",
                    **{
                        f"common name/{v}": True
                        for k in ["english name", "french name"]
                        for v in [p.pop(k, "")]
                        if v
                    },
                    **p,
                },
                self.priority.weight,
            )
            for p in self.model.get_perenial_plants()
        )
