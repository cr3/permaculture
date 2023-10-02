"""Design Ecologique database."""

from csv import reader
from functools import partial
from io import StringIO

from attrs import define, field
from bs4 import BeautifulSoup
from requests import Session
from yarl import URL

from permaculture.converter import Converter
from permaculture.database import DatabasePlugin, DatabasePlant
from permaculture.google import GoogleSpreadsheet
from permaculture.http import HTTPSession
from permaculture.locales import Locales
from permaculture.storage import Storage, null_storage


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
class DEConverter(Converter):
    locales: Locales = field(factory=partial(Locales.from_domain, "de"))

    def translate(self, message, context=None):
        """Translate `*` to None."""
        return None if message == "*" else super().translate(message, context)

    def convert_bool(self, key, value):
        """Convert `X` to True, `*` to False, otherwise None."""
        new_value = True if value == "X" else False if value == "*" else None
        return [(self.translate(key), new_value)]

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
            "Période de floraison": self.convert_letters,
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
class DEDatabase(DatabasePlugin):
    model: DEModel

    @classmethod
    def from_config(cls, config):
        model = DEModel.from_url(
            "https://designecologique.ca",
            config.storage,
        )
        return cls(model)

    def iterate(self):
        return (
            DatabasePlant(
                {
                    "scientific name": f"{p.pop('genus')} {p.pop('species')}",
                    "common name": [
                        p.pop("english name"),
                        p.pop("french name"),
                    ],
                    **p,
                }
            )
            for p in self.model.get_perenial_plants()
        )
