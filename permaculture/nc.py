"""Natural Capital website."""

import re
import string
from functools import partial

from attrs import define, field
from bs4 import BeautifulSoup
from requests import Session
from yarl import URL

from permaculture.database import DatabaseElement, DatabasePlugin
from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPClient
from permaculture.locales import Locales
from permaculture.storage import FileStorage, MemoryStorage


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
            raise NCAuthenticationError()

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
    client: HTTPClient = field()

    def view_complist(self, start):
        """View companion list."""
        response = self.client.get(
            "/plant-database/plant-companions-list",
            params={
                "vw": "complist",
                "start": start,
            },
        )
        return response.text

    def view_detail(self, Id):
        """View plant detail."""
        response = self.client.post(
            "/plant-database/new-the-plant-list",
            params={
                "vw": "detail",
                "id": Id,
            },
        )
        return response.text

    def view_list(self, sci_name="", sort_name=""):
        """View plant list."""
        response = self.client.post(
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
class NCModel:
    web: NCWeb
    locales: Locales = field(factory=partial(Locales.from_domain, "nc"))

    @classmethod
    def from_url(cls, url: URL, username: str, password: str, cache_dir=None):
        """Instantiate a Natural Capital model from URL."""
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        cache = HTTPCacheAll(storage)
        authentication = NCAuthentication(username, password)
        adapter = NCAdapter(authentication, cache=cache)
        client = HTTPClient(url).with_adapter(adapter)
        web = NCWeb(client)
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

    def convert(self, key, value):
        def to_str(old_value):
            return self.locales.translate(old_value, key).lower()

        def to_list(old_value):
            return [to_str(v) for v in re.split(r",\s+", old_value)]

        types = {
            "Soil Type": to_list,
            "Sun": to_list,
        }
        if isinstance(value, str):
            value = types.get(key, to_str)(value)
        return to_str(key), value

    def get_plant(self, Id):
        detail = self.web.view_detail(Id)
        return dict(
            self.convert(k, v) for k, v in self.parse_detail(detail).items()
        )

    def get_plants(self, sci_name="", sort_name=""):
        plant_list = self.web.view_list(sci_name, sort_name)
        for table in self.parse_tables(plant_list):
            yield dict(self.convert(k, v) for k, v in table.items())


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
            if re.match(scientific_name, plant["scientific name"], re.I):
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
