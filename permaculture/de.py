"""Design Ecologique database."""

import logging
import re
import string
from csv import reader
from functools import partial
from io import StringIO

from attrs import define, evolve, field
from bs4 import BeautifulSoup
from yarl import URL

from permaculture.browser import BrowserClient
from permaculture.converter import Converter
from permaculture.plant import IngestorPlant
from permaculture.google import GoogleSpreadsheet
from permaculture.locales import Locales
from permaculture.priority import LocationPriority, Priority
from permaculture.storage import Storage, null_storage

DE_ORIGIN = "https://designecologique.ca"

logger = logging.getLogger(__name__)


@define(frozen=True)
class DEWeb:
    """Design Ecologique web interface."""

    client: BrowserClient = field(factory=partial(BrowserClient, DE_ORIGIN))
    storage: Storage = field(default=null_storage)

    def with_cache(self, storage):
        client = self.client.with_cache(storage)
        return evolve(self, client=client, storage=storage)

    def source_url(self):
        """Return the origin URL for this data source."""
        return self.client.origin

    def perenial_plants_list(self):
        """List of perenial plants useful for permaculture in Quebec.

        :returns: Google spreadsheet with plants.
        """
        response = self.client.get("/liste-de-plantes-vivaces/")
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

    DISPATCH = {
        "Accumulateur de Nutriments": Converter.convert_ignore,
        "Comestible": Converter.convert_list,
        "Couleur de feuillage": Converter.convert_letters,
        "Couleur de floraison": Converter.convert_letters,
        "Couvre-sol": Converter.convert_ignore,
        "Cultivars intéressants": Converter.convert_ignore,
        "Eau": Converter.convert_letters,
        "Forme": Converter.convert_letters,
        "Fixateur Azote": Converter.convert_ignore,
        "Haie": Converter.convert_ignore,
        "Hauteur(m)": convert_range,
        "Inconvénient": Converter.convert_letters,
        "Intérêt automnale hivernal": Converter.convert_ignore,
        "Largeur(m)": convert_range,
        "Lien Information": Converter.convert_ignore,
        "Lumière": Converter.convert_letters,
        "Medicinal": convert_bool,
        "Multiplication": Converter.convert_letters,
        "Notes": Converter.convert_ignore,
        "Où peut-on la trouver?": Converter.convert_ignore,
        "Pollinisateurs": Converter.convert_letters,
        "Période de floraison": convert_period,
        "Période de taille": Converter.convert_list,
        "Racine": Converter.convert_letters,
        "Rythme de croissance": Converter.convert_letters,
        "Texture du sol": Converter.convert_letters,
        "Utilisation écologique": Converter.convert_list,
        "Vie sauvage": Converter.convert_letters,
        "pH (Min-Max)": convert_range,
    }


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
        next(csv)  # Skip blank row
        for row in csv:
            yield self.converter.convert(dict(zip(header, row, strict=True)))


@define(frozen=True)
class DEIngestor:
    name: str
    model: DEModel = field(factory=DEModel)
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config, name):
        """Instantiate DEIngestor from config."""
        model = DEModel().with_cache(config.storage)
        priority = LocationPriority("Quebec").with_cache(config.storage)
        return cls(name, model, priority)

    def fetch_all(self):
        count = 0
        for p in self.model.get_perenial_plants():
            count += 1
            if count % 100 == 0:
                logger.info("DE: ingested %d plants", count)
            yield IngestorPlant(
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
                ingestor=self.name,
                source=self.model.web.source_url(),
            )
        logger.info("DE: ingested %d plants total", count)
