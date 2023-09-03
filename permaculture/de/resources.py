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


def all_perenial_plants(de):
    data = de.perenial_plants().export(0)
    csv = reader(StringIO(data))
    next(csv)  # Skip groups
    header = [h.strip() for h in next(csv)]
    return [dict(zip(header, plant, strict=True)) for plant in csv]


def iterator(cache_dir=None):
    de = DesignEcologique.from_url(
        "https://designecologique.ca",
        cache_dir,
    )
    return [
        IteratorElement(
            f"{p['Genre']} {p['Espèce']}",
            list(filter(None, [p["Nom Anglais"], p["Nom français"]])),
            p,
        )
        for p in all_perenial_plants(de)
    ]
