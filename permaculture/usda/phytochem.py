"""USDA Phytochemical and Ethnobotanical Databases."""

import re
from abc import ABC, abstractmethod
from csv import DictReader
from functools import partial
from io import StringIO

from attrs import define, field
from bs4 import BeautifulSoup

from permaculture.converter import Converter
from permaculture.database import Database, DatabasePlant
from permaculture.http import HTTPSession
from permaculture.locales import Locales
from permaculture.priority import LocationPriority, Priority
from permaculture.tokenizer import tokenize

PHYTOCHEM_ORIGIN = "https://phytochem.nal.usda.gov"


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

    def search_results(self, q, et="", offset=0):
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

    def search(self, terms):
        """Search for terms in the databases."""
        offset = 0
        while True:
            response = self.web.search_results(terms, offset=offset)
            bs = BeautifulSoup(response["documentRecords"], "html.parser")
            token = tokenize(terms)
            for a in bs.select(".entity > a"):
                name = tokenize(a.text)
                if name == token:
                    yield PhytochemLink.from_url(a["href"], name, model=self)

            offset = response["lastRecord"]
            if offset > response["records"]:
                break


@define(frozen=True)
class PhytochemLink(ABC):
    Id: int
    Type: str
    name: str
    model: PhytochemModel = field(factory=PhytochemModel)

    @classmethod
    def from_url(cls, url, name, **kwargs):
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
        return cls(Id, Type, name, **kwargs)

    @abstractmethod
    def get_plant(self):
        """Get the plant for this type."""


class PhytochemEthnoplant(PhytochemLink):
    def get_plant(self):
        rows = self.model.download_csv(
            self.Id,
            self.Type,
            column="uses",
        )
        return self.model.converter.convert(
            {
                "scientific name": self.name,
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
                "scientific name": self.name,
                **{
                    f"chemical/{row['Chemical']}": int(row["Activity Count"])
                    for row in rows
                },
            }
        )


@define(frozen=True)
class PhytochemDatabase(Database):
    model: PhytochemModel = field(factory=PhytochemModel)
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config):
        """Instantiate PhytochemDatabase from config."""
        model = PhytochemModel().with_cache(config.storage)
        priority = LocationPriority("United States").with_cache(config.storage)
        return cls(model, priority)

    def lookup(self, *scientific_names):
        # TODO: Do we really need to tokenize scientific names?
        [tokenize(n) for n in scientific_names]
        for sci_name in scientific_names:
            for link in self.model.search(sci_name):
                yield DatabasePlant(link.get_plant(), self.priority.weight)
