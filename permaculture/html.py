"""HTML utilities."""

from collections import defaultdict
from itertools import count

from bs4 import BeautifulSoup


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
