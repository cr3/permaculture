"""Natural Capital website."""

import logging
import re
import string
from concurrent.futures import ThreadPoolExecutor
from functools import cache, partial

from attrs import define, field
from bs4 import BeautifulSoup
from requests import Session
from yarl import URL

from permaculture.converter import FLOAT_RE, Converter
from permaculture.database import Database, DatabasePlant
from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPSession
from permaculture.locales import Locales
from permaculture.nlp import normalize
from permaculture.priority import LocationPriority, Priority
from permaculture.storage import null_storage
from permaculture.unit import feet, inches

NC_ORIGIN = "https://permacultureplantdata.com"

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
    session: HTTPSession = field(factory=partial(HTTPSession, NC_ORIGIN))

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

    def view_list(self, sci_name="", sort_name="", limit_start=0):
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
                "limitstart": limit_start,
            },
        )
        return response.text


@define(frozen=True)
class NCConverter(Converter):
    locales: Locales = field(factory=partial(Locales.from_domain, "nc"))

    def convert_period(self, key, value):
        if value is None or not value.strip():
            return []

        k = self.translate(key)
        n = [self.translate(v, key) for v in re.split(r"\s*-\s*", value)]
        match len(n):
            case 1:
                return [(f"{k}/min", n[0]), (f"{k}/max", n[0])]
            case 2:
                return [(f"{k}/min", n[0]), (f"{k}/max", n[1])]
            case _:
                raise ValueError(f"Unknown period: {value!r}")

    def convert_range(self, key, value, unit=1.0):
        if m := re.match(rf"{FLOAT_RE} (?P<u>\w+)", value):
            u = m.group("u")
            match u:
                case "inches":
                    unit = inches
                case "feet":
                    unit = feet
                case _:
                    raise ValueError(f"Unknown range unit: {u!r}")

        return super().convert_range(key, value, unit)

    def convert_item(self, key, value):
        dispatchers = {
            "Bacteria-Fungal Ratio": self.convert_ignore,
            "Bloom Time": self.convert_period,
            "Common name": self.convert_list,
            "Compatible": self.convert_bool,
            "Fire Damage": self.convert_list,
            "Flood": self.convert_list,
            "Flower Color": self.convert_list,
            "Fruit Time": self.convert_period,
            "Growth Rate": self.convert_list,
            "Height": self.convert_range,
            "Minimum Root Depth": partial(self.convert_float, unit=inches),
            "Notes": self.convert_ignore,
            "Root Type": self.convert_list,
            "Soil Moisture": self.convert_list,
            "Soil Type": self.convert_list,
            "Soil pH": self.convert_range,
            "Spread": self.convert_range,
            "Sun": self.convert_list,
            "USDA Hardiness Zones": self.convert_range,
        }
        return dispatchers.get(key, self.convert_string)(key, value)


@define(frozen=True)
class NCModel:
    web: NCWeb = field(factory=NCWeb)
    converter: NCConverter = field(factory=NCConverter)

    def with_authentication(
        self, username: str, password: str, storage=null_storage
    ):
        """Add authentication credentials to the model."""
        cache = HTTPCacheAll(storage)
        authentication = NCAuthentication(username, password)
        adapter = NCAdapter(authentication, cache=cache)
        self.web.session.with_adapter(adapter)
        return self

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

    def parse_items(self, table):
        """Parse the items total inside a bold tag."""
        b = table.find("b")
        m = re.match(r"Items \d+ - \d+ of (?P<total>\d+)", b.text)
        if not m:
            raise ValueError(f"Expected Items, got {b.text!r}")

        return int(m.group("total"))

    def parse_plant_total(self, text):
        """Parse a plant list consisting of an HTML table of plants."""
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.select("table[width='100%']")
        for table in tables:
            if table.find("td", attrs={"width": "50%"}):
                return self.parse_items(table)

        return -1

    def get_plant_total(self):
        """Get the total number of plants."""
        text = self.web.view_list()
        return self.parse_plant_total(text)

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
        """Get plant details by Id."""
        detail = self.web.view_detail(Id)
        data = self.parse_detail(detail)
        return self.converter.convert(data)

    def get_plants(self, sci_name="", sort_name="", limit_start=0):
        """Get plants by scientific name or by common name."""
        try:
            plant_list = self.web.view_list(sci_name, sort_name, limit_start)
        except NCAuthenticationError as error:
            logger.info(
                "Skipping Natural Capital: %(error)s", {"error": error}
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
class NCDatabase(Database):
    model: NCModel = field(factory=NCModel)
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config):
        """Instantiate NCDatabase from config."""
        model = NCModel().with_authentication(
            config.nc_username,
            config.nc_password,
            config.storage,
        )
        priority = LocationPriority("United States").with_cache(config.storage)
        return cls(model, priority)

    def companions(self, compatible):
        # Additional cache to speedup getting the same plants.
        get_plant = cache(self.model.get_plant)

        def get_element(companion):
            plant = get_plant(companion["plant"].Id)
            related = get_plant(companion["related"].Id)
            return (
                DatabasePlant(plant, self.priority.weight),
                DatabasePlant(related, self.priority.weight),
            )

        with ThreadPoolExecutor() as executor:
            yield from executor.map(
                get_element,
                (
                    c
                    for c in self.model.get_all_plant_companions()
                    if "related" in c and c["compatible"] == compatible
                ),
            )

    def iterate(self):
        def get_plants(limit_start):
            return [
                DatabasePlant(
                    self.model.get_plant(plant["plant name"].Id),
                    self.priority.weight,
                )
                for plant in self.model.get_plants(limit_start=limit_start)
            ]

        total = self.model.get_plant_total()
        with ThreadPoolExecutor() as executor:
            results = executor.map(get_plants, range(0, total, 50))

        return (plant for plants in results for plant in plants)

    def lookup(self, *scientific_names):
        # The search in the web interface concatenates words, so
        # searching for "symphytum officinale" actually searches for
        # "symphytumofficinale" which doesn't match anything. This
        # workaround searches each word and the iterates over all
        # the matches for the plants that match the full name.
        seen = set()
        tokens = [normalize(n) for n in scientific_names]
        for sci_name in tokens:
            for part in sci_name.split():
                for plant in self.model.get_plants(sci_name=part):
                    name = plant["scientific name"]
                    if name not in seen and name in tokens:
                        seen.add(name)
                        yield DatabasePlant(
                            self.model.get_plant(plant["plant name"].Id),
                            self.priority.weight,
                        )

    def search(self, common_name):
        # Same comment as in the `lookup` method.
        seen = set()
        for part in common_name.split():
            for plant in self.model.get_plants(sort_name=part):
                name = plant["plant name"].text
                if name not in seen and all(
                    re.search(n, name, re.I) for n in common_name.split()
                ):
                    seen.add(name)
                    yield DatabasePlant(
                        self.model.get_plant(plant["plant name"].Id),
                        self.priority.weight,
                    )
