"""USDA Phytochemical and Ethnobotanical Databases."""

import logging
import re
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from csv import DictReader
from functools import partial
from io import StringIO
from itertools import chain

from attrs import define, field
from bs4 import BeautifulSoup

from permaculture.converter import Converter
from permaculture.database import Database, DatabasePlant
from permaculture.http import HTTPSession
from permaculture.locales import Locales
from permaculture.tokenizer import tokenize

PHYTOCHEM_ORIGIN = "https://phytochem.nal.usda.gov"

logger = logging.getLogger(__name__)


@define(frozen=True)
class PhytochemWeb:
    session: HTTPSession = field(
        factory=partial(HTTPSession, PHYTOCHEM_ORIGIN),
    )

    def download(
        self, Id, Type, filetype="csv", name="", order="asc", **params
    ):
        """Download plant data by Id."""
        params = {
            "filetype": filetype,
            "name": name,
            "order": order,
            "type": Type,
            **params,
        }
        response = self.session.get(
            f"/phytochem/download/{Id}",
            params=params,
        )
        return response.text

    def search_results(self, q="", et="", offset=0):
        """Search for plants using scientific or common names.

        :param q: Scientific or common name.
        :param et: Entity type: A (Biological Activity), C (Chemicals),
            P (Plants), S (Syndrome), E (Ethnobotanical Plants),
            U (Ethnobotanical Uses), defaults to all.
        :param offset: Record offset when paginating.
        """
        params = {
            "et": et,
            "q": q,
            "offset": offset,
        }
        response = self.session.get(
            "/phytochem/search-results",
            params=params,
        )
        return response.json()


@define(frozen=True)
class PhytochemConverter(Converter):
    locales: Locales = field(
        factory=partial(Locales.from_domain, "usda-phytochem"),
    )


@define(frozen=True)
class PhytochemModel:
    """USDA Phytochemical model."""

    web: PhytochemWeb = field(factory=PhytochemWeb)
    converter: PhytochemConverter = field(factory=PhytochemConverter)

    def with_cache(self, storage):
        self.web.session.with_cache(storage)
        return self

    def download_csv(self, Id, Type, **params):
        text = self.web.download(Id, Type, filetype="csv", **params)
        yield from DictReader(StringIO(text))

    def search(self, q="", et=""):
        """Search for terms in the databases."""
        offset = 0
        while True:
            response = self.web.search_results(q=q, et=et, offset=offset)
            bs = BeautifulSoup(response["documentRecords"], "html.parser")
            for e in bs.select(".entity"):
                if m := re.search(r"\((.+)\)", e.text):
                    common_names = [n.strip() for n in m.group(1).split(";")]
                else:
                    common_names = []

                try:
                    yield PhytochemLink.from_url(
                        e.a["href"],
                        e.a.text,
                        common_names=common_names,
                        model=self,
                    )
                except ValueError as error:
                    logger.info(f"Skipping plant: {error}")

            offset = response["lastRecord"]
            if offset > response["records"]:
                break


@define(frozen=True)
class PhytochemLink(ABC):
    Id: int
    Type: str
    scientific_name: str
    common_names: list[str] = field(factory=list)
    model: PhytochemModel = field(factory=PhytochemModel)

    @classmethod
    def from_url(cls, url, scientific_name, **kwargs):
        m = re.match(r"/phytochem/(?P<Type>\w+)/show/(?P<Id>\d+)$", url)
        if not m:
            raise ValueError(f"Unsupported url: {url}")

        Type = m.group("Type")
        match Type:
            case "ethnoplants":
                cls = PhytochemEthnoplant
            case "plants":
                cls = PhytochemPlant
            case _:
                raise ValueError(f"Unsupported type: {Type}")

        Id = int(m.group("Id"))
        return cls(Id, Type, scientific_name, **kwargs)

    def get_plant(self):
        """Get the plant for this type."""
        return {
            "scientific name": self.scientific_name,
            **{f"common name/{n}": True for n in self.common_names},
        }


class PhytochemEthnoplant(PhytochemLink):
    def get_plant(self):
        rows = self.model.download_csv(
            self.Id,
            self.Type,
            column="uses",
        )
        return self.model.converter.convert(
            {
                **super().get_plant(),
                **{f"use/{row['Ethnobotanical Use']}": True for row in rows},
            }
        )


class PhytochemPlant(PhytochemLink):
    def get_plant(self):
        rows = self.model.download_csv(
            self.Id,
            self.Type,
            column="chemical_value",
            view="allChem",
        )
        return self.model.converter.convert(
            {
                **super().get_plant(),
                **{
                    f"chemical/{r['Chemical']}": int(r["Activity Count"])
                    for r in rows
                },
            }
        )


@define(frozen=True)
class PhytochemDatabase(Database):
    model: PhytochemModel = field(factory=PhytochemModel)

    @classmethod
    def from_config(cls, config):
        """Instantiate PhytochemDatabase from config."""
        model = PhytochemModel().with_cache(config.storage)
        return cls(model)

    def iterate(self):
        def get_plants(et):
            return [
                DatabasePlant(
                    self.model.converter.convert(
                        {
                            "scientific name": link.scientific_name,
                            **{
                                f"common name/{n}": True
                                for n in link.common_names
                            },
                        }
                    )
                )
                for link in self.model.search(et=et)
            ]

        with ThreadPoolExecutor() as executor:
            yield from chain.from_iterable(
                executor.map(get_plants, ("E", "P"))
            )

    def lookup(self, *scientific_names):
        tokens = [tokenize(n) for n in scientific_names]
        return (
            DatabasePlant(link.get_plant())
            for token in tokens
            for link in self.model.search(q=token)
            if tokenize(link.scientific_name) in tokens
        )

    def search(self, common_name):
        token = tokenize(common_name)
        return (
            DatabasePlant(link.get_plant())
            for link in self.model.search(q=token)
            if token in map(tokenize, link.common_names)
        )
