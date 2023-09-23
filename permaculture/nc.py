"""Natural Capital website."""

import logging
import re
import string
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from attrs import define, field
from bs4 import BeautifulSoup
from requests import Session
from yarl import URL

from permaculture.converter import Converter
from permaculture.database import DatabasePlant, DatabasePlugin
from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPSession
from permaculture.locales import Locales
from permaculture.storage import null_storage
from permaculture.tokenizer import tokenize
from permaculture.unit import inches

logger = logging.getLogger(__name__)


class NCAuthenticationError(Exception):
    """Raised when authentication fails."""


@define(frozen=True)
class NCAuthentication:
    username: str = field()
    password: str = field()
    session: Session = field(factory=Session)

    def get_payload(self, request):
        response = self.session.get(request.url)
        bs = BeautifulSoup(response.text, "html.parser")
        inputs = bs.find("form", attrs={"name": "btl-formlogin"})
        return {
            "bttask": inputs.find(attrs={"name": "bttask"}).get("value"),
            "username": self.username,
            "passwd": self.password,
            "return": inputs.find(attrs={"name": "return"}).get("value"),
            inputs.find(attrs={"value": "1"}).get("name"): "1",
            "remember": "yes",
        }

    def authenticate(self, request):
        payload = self.get_payload(request)
        response = self.session.post(request.url, data=payload)
        if not response.cookies:
            raise NCAuthenticationError(
                f"Failed authenticating to {request.url}"
            )

        request.prepare_cookies(response.cookies)
        request.headers["X-Cache-All"] = "overwrite"
        return response.headers["Set-Cookie"]


class NCAdapter(HTTPCacheAdapter):
    def __init__(self, authentication, **kwargs):
        super().__init__(**kwargs)
        self.authentication = authentication

    def send(self, request, *args, **kwargs):  # pragma: no cover
        response = super().send(request, *args, **kwargs)
        if response.headers.get("X-Logged-In", "False") == "False":
            cookie = self.authentication.authenticate(request)
            response = super().send(request, *args, **kwargs)
            response.raw._original_response.msg.add_header(
                "Set-Cookie", cookie
            )

        return response


@define(frozen=True)
class NCWeb:
    session: Session = field()

    def view_complist(self, start):
        """View companion list."""
        response = self.session.get(
            "/plant-database/plant-companions-list",
            params={
                "vw": "complist",
                "start": start,
            },
        )
        return response.text

    def view_detail(self, Id):
        """View plant detail."""
        response = self.session.post(
            "/plant-database/new-the-plant-list",
            params={
                "vw": "detail",
                "id": Id,
            },
        )
        return response.text

    def view_list(self, sci_name="", sort_name=""):
        """View plant list."""
        response = self.session.post(
            "/plant-database/new-the-plant-list",
            params={
                "vw": "list",
            },
            data={
                "sortName": sort_name,
                "sciName": sci_name,
                "bfilter": "Set Filter",
            },
        )
        return response.text


@define(frozen=True)
class NCConverter(Converter):
    locales: Locales = field(factory=partial(Locales.from_domain, "nc"))

    def convert_item(self, key, value):
        dispatchers = {
            "Bacteria-Fungal Ratio": self.convert_float,
            "Compatible": self.convert_bool,
            "Height": partial(self.convert_range, unit=inches),
            "Minimum Root Depth": partial(self.convert_float, unit=inches),
            "Notes": self.convert_ignore,
            "Soil Type": self.convert_list,
            "Soil pH": self.convert_range,
            "Spread": partial(self.convert_range, unit=inches),
            "Sun": self.convert_list,
            "USDA Hardiness Zones": self.convert_range,
        }
        return dispatchers.get(key, self.convert_string)(key, value)


@define(frozen=True)
class NCModel:
    web: NCWeb
    converter: NCConverter = field(factory=NCConverter)

    @classmethod
    def from_url(
        cls, url: URL, username: str, password: str, storage=null_storage
    ):
        """Instantiate a Natural Capital model from URL."""
        cache = HTTPCacheAll(storage)
        authentication = NCAuthentication(username, password)
        adapter = NCAdapter(authentication, cache=cache)
        session = HTTPSession(url).with_adapter(adapter)
        web = NCWeb(session)
        return cls(web)

    def parse_tr(self, row):
        """Parse a table row into an iterator of text or links."""
        for td in row.find_all("td"):
            text = td.get_text()
            a = td.find("a")
            if a:
                yield NCLink(text, URL(a["href"]))
            else:
                yield text

    def parse_table(self, table):
        """Parse a table with a header into a list of dictionaries."""
        header, *trs = table.find_all("tr")
        keys = [td.get_text().strip() for td in header.find_all("td")]
        for tr in trs:
            values = self.parse_tr(tr)
            yield dict(zip(keys, values, strict=True))

    def parse_plant_list(self, text):
        """Parse a plant list consisting of an HTML table of plants."""
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.select("table[width='100%']")
        for table in tables:
            if table.find("td", attrs={"class": "plantList"}):
                yield from self.parse_table(table)

    def get_plant_companions(self, letter):
        """Get plant companions for a single letter."""
        last_plant = None
        for plant in self.parse_plant_list(self.web.view_complist(letter)):
            if not plant["Plant"]:
                plant["Plant"] = last_plant["Plant"]
            else:
                last_plant = plant

            if not plant["Related Plant"].Id:
                plant["Related Plant"] = None

            yield self.converter.convert(plant)

    def get_all_plant_companions(self):
        """Get plant companions for all letters."""
        for letter in string.ascii_uppercase:
            yield from self.get_plant_companions(letter)

    def parse_key_value(self, key_value):
        """Parse a bold key and roman value."""
        prefix = key_value.find("b").text
        key = prefix.strip(": ")
        value = key_value.text.removeprefix(prefix).strip()
        return key, value

    def parse_detail(self, text):
        """Parse a plant detail consisting of an HTML table and paragraphs."""
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.select("table[width='100%']:not([class*=list])")
        detail = {}
        for table in tables:
            for tr in table.find_all("tr"):
                for td in tr.find_all("td"):
                    ps = td.find_all("p")
                    if ps:
                        for p in ps:
                            key, value = self.parse_key_value(p)
                            detail[key] = value

                        continue

                    b = td.find("b")
                    if b:
                        key, value = self.parse_key_value(td)
                        detail[key] = value
                        continue

        return detail

    def get_plant(self, Id):
        detail = self.web.view_detail(Id)
        data = self.parse_detail(detail)
        return self.converter.convert(data)

    def get_plants(self, sci_name="", sort_name=""):
        try:
            plant_list = self.web.view_list(sci_name, sort_name)
        except NCAuthenticationError as error:
            logger.debug(
                "Skipping Nature Capital: %(error)s", {"error": error}
            )
            return

        for table in self.parse_plant_list(plant_list):
            yield self.converter.convert(table)


@define(frozen=True)
class NCLink:
    text: str
    url: URL = field(converter=URL)

    @property
    def Id(self):
        return int(self.url.query["id"])

    def __str__(self):
        return self.text


@define(frozen=True)
class NCDatabase(DatabasePlugin):
    model: NCModel

    @classmethod
    def from_config(cls, config):
        model = NCModel.from_url(
            "https://permacultureplantdata.com",
            config.nc_username,
            config.nc_password,
            config.storage,
        )
        return cls(model)

    def companions(self, compatible):
        def get_element(companion):
            plant = self.model.get_plant(companion["plant"].Id)
            related = self.model.get_plant(companion["related"].Id)
            return (DatabasePlant(plant), DatabasePlant(related))

        with ThreadPoolExecutor() as executor:
            yield from executor.map(
                get_element,
                (
                    c
                    for c in self.model.get_all_plant_companions()
                    if c["related"] and c["compatible"] == compatible
                ),
            )

    def lookup(self, scientific_name):
        # Workaround crappy search in the web interface.
        name = scientific_name.split()[0]
        token = tokenize(scientific_name)
        return (
            DatabasePlant(self.model.get_plant(plant["plant name"].Id))
            for plant in self.model.get_plants(sci_name=name)
            if plant["scientific name"] == token
        )

    def search(self, common_name):
        # Workaround crappy search in the web interface.
        name = common_name.split()[0]
        return (
            DatabasePlant(self.model.get_plant(plant["plant name"].Id))
            for plant in self.model.get_plants(sort_name=name)
            if re.match(common_name, plant["plant name"].text, re.I)
        )
