"""Wikipedia API."""

from collections import defaultdict
from itertools import count

from attrs import define
from bs4 import BeautifulSoup

from permaculture.http import HTTPSession
from permaculture.storage import null_storage


@define(frozen=True)
class Wikipedia:
    """Wikipedia API."""

    session: HTTPSession

    @classmethod
    def from_url(cls, url, storage=null_storage):
        """Instantiate Wikipedia from URL."""
        session = HTTPSession(url).with_cache(storage)
        return cls(session)

    def get(self, action="query", **kwargs):
        params = {
            "format": "json",
            "redirects": 1,
            "action": action,
            **kwargs,
        }
        return self.session.get("", params=params).json()

    def get_text(self, page):
        data = self.get("parse", prop="text", page=page)
        return data["parse"]["text"]["*"]


def parse_table(table):
    """Parse an HTML table into a dictionary of values."""
    data = defaultdict(list)
    headers = {}
    for tr in table.find_all("tr"):
        if ths := tr.find_all("th"):
            # Repeat headers across colspan.
            names = [
                th.get_text().strip()
                for th in ths
                for _ in range(int(th.attrs.get("colspan", "1")))
            ]
            # Skip duplicate headers.
            if names != [v[-1] for v in headers.values()]:
                headers = {
                    i: (*headers.get(i, ()), name)
                    for i, name in zip(count(), names)
                }

        for i, td in enumerate(tr.find_all("td")):
            key = headers.get(i, i)
            data[key].append(td.get_text())

    return data


def parse_tables(text, **kwargs):
    """Parse HTML text into a list of tables."""
    soup = BeautifulSoup(text, "html.parser")
    return [parse_table(table) for table in soup.find_all("table", **kwargs)]
