"""Wikipedia API."""

import re
from collections import defaultdict
from functools import partial
from itertools import count

import pandas as pd
from attrs import define
from bs4 import BeautifulSoup
from requests import Session

from permaculture.http import HTTPSession
from permaculture.storage import null_storage


@define(frozen=True)
class Wikipedia:
    """Wikipedia API."""

    session: Session

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
                    for i, name in zip(count(), names)  # noqa: B905
                }

        for i, td in enumerate(tr.find_all("td")):
            key = headers.get(i, i)
            data[key].append(td.get_text())

    return data


def parse_tables(text, **kwargs):
    """Parse HTML text into a list of tables."""
    soup = BeautifulSoup(text, "html.parser")
    return [parse_table(table) for table in soup.find_all("table", **kwargs)]


def get_companion_plants(wikipedia):
    """Get companion plants from Wikipedia and return a DataFrame."""
    text = wikipedia.get_text("List_of_companion_plants")
    tables = parse_tables(text, class_=lambda x: not x)
    multi_dfs = [pd.DataFrame(t) for t in tables]
    dfs = [
        df[category].assign(Category=category)
        for df in multi_dfs
        for category in [df.columns[0][0]]
    ]
    df = pd.concat(dfs, ignore_index=True)
    df["Helps"] = (
        df["Helps"]
        .apply(partial(re.sub, r"\[.+?\]", ""))
        .apply(partial(re.sub, r"\W+$", ""))
    )
    return df
