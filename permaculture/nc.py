"""Natural Capital website."""

import string

from attrs import define, field
from bs4 import BeautifulSoup
from requests import Session
from yarl import URL

from permaculture.http import HTTPCacheAdapter, HTTPCacheAll, HTTPClient
from permaculture.storage import FileStorage, MemoryStorage


class NaturalCapitalAuthenticationError(Exception):
    """Raised when authentication fails."""


@define(frozen=True)
class NaturalCapitalAuthentication:
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
            raise NaturalCapitalAuthenticationError()

        request.prepare_cookies(response.cookies)
        request.headers["X-Cache-All"] = "overwrite"
        return response.headers["Set-Cookie"]


class NaturalCapitalAdapter(HTTPCacheAdapter):
    def __init__(self, authentication, **kwargs):
        super().__init__(**kwargs)
        self.authentication = authentication

    def send(self, request, *args, **kwargs):
        response = super().send(request, *args, **kwargs)
        if response.headers.get("X-Logged-In", "False") == "False":
            cookie = self.authentication.authenticate(request)
            response = super().send(request, *args, **kwargs)
            response.raw._original_response.msg.add_header(
                "Set-Cookie", cookie
            )

        return response


@define(frozen=True)
class NaturalCapital:
    client: HTTPClient = field()
    cache_dir: str = field(default=None)

    @classmethod
    def from_url(cls, url: URL, username: str, password: str, cache_dir=None):
        """Instantiate Natural Capital from URL."""
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        cache = HTTPCacheAll(storage)
        authentication = NaturalCapitalAuthentication(username, password)
        adapter = NaturalCapitalAdapter(authentication, cache=cache)
        client = HTTPClient.with_adapter(url, adapter)
        return cls(client, cache_dir)

    def plant_companions_list(self, start):
        response = self.client.get(
            "/plant-database/plant-companions-list",
            params={
                "vw": "complist",
                "start": start,
            },
        )
        return response.text


def get_plant_companions(nc, letter):
    text = nc.plant_companions_list(letter)
    soup = BeautifulSoup(text, "html.parser")
    table = soup.find("table", attrs={"width": "100%"})
    header, *rows = table.find_all("tr")
    keys = [td.get_text().strip() for td in header.find_all("td")]
    for row in rows:
        values = (td.get_text() for td in row.find_all("td"))
        yield dict(zip(keys, values))


def get_all_plant_companions(nc):
    for letter in string.ascii_uppercase:
        yield from get_plant_companions(nc, letter)
