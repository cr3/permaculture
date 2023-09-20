"""Natural Capital website."""

import logging
import re
import string
from functools import partial
from itertools import chain

from attrs import define, field
from bs4 import BeautifulSoup
from requests import Session
from yarl import URL

from permaculture.database import DatabaseElement, DatabasePlugin
from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPSession
from permaculture.locales import Locales
from permaculture.storage import FileStorage, MemoryStorage
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
class NCConverter:
    locales: Locales = field(factory=partial(Locales.from_domain, "nc"))

    def translate(self, message, context=None):
        """Convenience function to translate from locales."""
        return self.locales.translate(message, context).lower()

    def convert_ignore(self, *_):
        return []

    def convert_float(self, key, value, unit=1.0):
        # TODO: match unit inside this regex.
        new_value = re.match(r"([0-9.]+)", value).group(1)
        return [(self.translate(key), float(new_value) * unit)]

    def convert_list(self, key, value):
        k = self.translate(key)
        new_value = [self.translate(v, key) for v in re.split(r",\s+", value)]
        return [(f"{k}/{v}", True) for v in new_value]

    def convert_range(self, key, value, unit=1.0):
        k = self.translate(key)
        n = [float(i) * unit for i in re.findall(r"[0-9.]+", value)]
        match len(n):
            case 2:
                return [(f"{k}/min", n[0]), (f"{k}/max", n[1])]
            case 1:
                return [(f"{k}/min", n[0]), (f"{k}/max", n[0])]
            case 0:
                return []
            case _:
                raise ValueError(f"Unsupported range: {value}")

    def convert_string(self, key, value):
        if isinstance(value, str):
            value = self.translate(value)
        return [(self.translate(key), value)]

    def convert_item(self, key, value):
        dispatchers = {
            "Height": partial(self.convert_range, unit=inches),
            "Minimum Root Depth": partial(self.convert_float, unit=inches),
            "Notes": self.convert_ignore,
            "Reference": self.convert_ignore,
            "Soil Type": self.convert_list,
            "Soil pH": self.convert_range,
            "Spread": partial(self.convert_range, unit=inches),
            "Sun": self.convert_list,
            "USDA Hardiness Zones": self.convert_range,
        }
        return dispatchers.get(key, self.convert_string)(key, value)

    def convert(self, data):
        return dict(
            chain.from_iterable(
                self.convert_item(k, v) for k, v in data.items()
            )
        )


@define(frozen=True)
class NCModel:
    web: NCWeb
    converter: NCConverter = field(factory=NCConverter)

    @classmethod
    def from_url(cls, url: URL, username: str, password: str, cache_dir=None):
        """Instantiate a Natural Capital model from URL."""
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
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
        header, *trs = table.find_all("tr")
        keys = [td.get_text().strip() for td in header.find_all("td")]
        for tr in trs:
            values = self.parse_tr(tr)
            yield dict(zip(keys, values, strict=True))

    def parse_tables(self, text):
        """Parse a table with header into a list of dictionaries."""
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.find_all("table", attrs={"width": "100%"})
        for table in tables:
            if table.find("td", attrs={"class": "plantList"}):
                yield from self.parse_table(table)

    def get_plant_companions(self):
        for letter in string.ascii_uppercase:
            companions_list = self.web.view_complist(letter)
            yield from self.parse_tables(companions_list)

    def parse_key_value(self, key_value):
        prefix = key_value.find("b").text
        key = prefix.strip(": ")
        value = key_value.text.removeprefix(prefix).strip()
        return key, value

    def parse_detail(self, text):
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.find_all("table", attrs={"width": "100%"})
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

        for table in self.parse_tables(plant_list):
            yield self.converter.convert(table)


@define(frozen=True)
class NCLink:
    text: str
    url: URL = field(converter=URL)

    @property
    def identifier(self):
        return self.url.query["id"]

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
            config.cache_dir,
        )
        return cls(model)

    def lookup(self, scientific_name):
        # Workaround crappy search in the web interface.
        name = scientific_name.split()[0]
        for plant in self.model.get_plants(sci_name=name):
            if re.match(f"{scientific_name}$", plant["scientific name"], re.I):
                detail = self.model.get_plant(plant["plant name"].identifier)

                yield DatabaseElement(
                    "NC",
                    detail["scientific name"],
                    [detail["common name"]],
                    detail,
                )

    def search(self, common_name):
        # Workaround crappy search in the web interface.
        name = common_name.split()[0]
        for plant in self.model.get_plants(sort_name=name):
            if re.match(common_name, plant["plant name"].text, re.I):
                detail = self.model.get_plant(plant["plant name"].identifier)

                yield DatabaseElement(
                    "NC",
                    detail["scientific name"],
                    [detail["common name"]],
                    detail,
                )
