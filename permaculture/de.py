"""Design Ecologique database."""

import re
from csv import reader
from functools import partial
from io import StringIO

from attrs import define, field
from bs4 import BeautifulSoup
from requests import Session
from yarl import URL

from permaculture.database import DatabaseElement, DatabaseIterablePlugin
from permaculture.google import GoogleSpreadsheet
from permaculture.http import HTTPSession
from permaculture.locales import Locales


@define(frozen=True)
class DEWeb:
    """Design Ecologique web interface."""

    session: Session = field()
    _cache_dir = field(default=None)

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
        return GoogleSpreadsheet.from_url(url, self._cache_dir)


@define(frozen=True)
class DEModel:
    web: DEWeb = field()
    locales: Locales = field(factory=partial(Locales.from_domain, "de"))

    @classmethod
    def from_url(cls, url: URL, cache_dir=None):
        """Instantiate a Design Ecologique model from URL."""
        session = HTTPSession(url).with_cache(cache_dir)
        web = DEWeb(session)
        return cls(web)

    def convert(self, key, value):
        def to_range(v):
            v = v.replace(",", ".").strip()
            if re.match(r"\d+", v):
                return [float(x) for x in re.split("\\s*[\u2013-]\\s*", v)]
            else:
                return []

        def to_str(old_value):
            return self.locales.translate(old_value, key)

        def to_list(old_value):
            new_value = [to_str(v) for v in re.split(r",?\s+", old_value)]
            if len(new_value) == 1 and new_value[0] == old_value:
                new_value = [to_str(v) for v in old_value]

            return new_value

        types = {
            "Comestible": to_list,
            "Couleur de feuillage": to_list,
            "Couleur de floraison": to_list,
            "Eau": to_list,
            "Forme": to_list,
            "Inconvénient": to_list,
            "Intérêt automnale hivernal": to_list,
            "Lumière": to_list,
            "Multiplication": to_list,
            "Pollinisateurs": to_list,
            "Période de floraison": to_list,
            "Période de taille": to_list,
            "Racine": to_list,
            "Rythme de croissance": to_list,
            "Texture du sol": to_list,
            "Utilisation écologique": to_list,
            "Vie sauvage": to_list,
            "Hauteur(m)": to_range,
            "Largeur(m)": to_range,
        }
        new_value = types.get(key, to_str)(value)
        return to_str(key), new_value

    def get_perenial_plants(self):
        data = self.web.perenial_plants_list().export(0)
        csv = reader(StringIO(data))
        next(csv)  # Skip groups
        header = [h.strip() for h in next(csv)]
        for row in csv:
            yield dict(
                self.convert(k, v) for k, v in zip(header, row, strict=True)
            )


@define(frozen=True)
class DEDatabase(DatabaseIterablePlugin):
    model: DEModel

    @classmethod
    def from_config(cls, config):
        model = DEModel.from_url(
            "https://designecologique.ca",
            config.cache_dir,
        )
        return cls(model)

    def iterate(self):
        for p in self.model.get_perenial_plants():
            yield DatabaseElement(
                "DE",
                f"{p['genus']} {p['species']}",
                [p["common name"]],
                p,
            )
