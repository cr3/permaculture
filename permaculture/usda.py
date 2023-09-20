"""USDA Plants database."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from itertools import chain

from attrs import define, field
from requests import Session
from yarl import URL

from permaculture.database import DatabaseElement, DatabaseIterablePlugin
from permaculture.http import HTTPSession
from permaculture.locales import Locales
from permaculture.storage import FileStorage, MemoryStorage, Storage
from permaculture.tokenizer import tokenize


@define(frozen=True)
class USDAWeb:
    """USDA web interface."""

    session: Session

    def characteristics_search(self) -> bytes:
        """Search characteristics."""
        payload = {
            "Text": None,
            "Field": None,
            "Locations": None,
            "Groups": None,
            "Durations": None,
            "GrowthHabits": None,
            "WetlandRegions": None,
            "NoxiousLocations": None,
            "InvasiveLocations": None,
            "Countries": None,
            "Provinces": None,
            "Counties": None,
            "Cities": None,
            "Localities": None,
            "ArtistFirstLetters": None,
            "ImageLocations": None,
            "Artists": None,
            "CopyrightStatuses": None,
            "ImageTypes": None,
            "SortBy": "sortSciName",
            "Offset": None,
            "FilterOptions": None,
            "UnfilteredPlantIds": None,
            "Type": "Characteristics",
            "TaxonSearchCriteria": None,
            "MasterId": -1,
        }
        response = self.session.post(
            "/api/CharacteristicsSearch", json=payload
        )
        return response.json()

    def plant_profile(self, symbol):
        """Plant profile for a symbol."""
        response = self.session.get(
            "/api/PlantProfile", params={"symbol": symbol}
        )
        return response.json()

    def plant_characteristics(self, Id):
        """Plant characteristics for an identifier."""
        response = self.session.get(f"/api/PlantCharacteristics/{Id}")
        return response.json()


@define(frozen=True)
class USDAConverter:
    locales: Locales = field(factory=partial(Locales.from_domain, "usda"))

    def translate(self, message, context=None):
        """Convenience function to translate from locales."""
        return self.locales.translate(message, context).lower()

    def convert_ignore(self, *_):
        return []

    def convert_bool(self, key, value):
        if value == "Yes":
            return [(self.translate(key), True)]
        elif value == "No":
            return [(self.translate(key), False)]
        else:
            raise ValueError(f"Unknown boolean: {value}")

    def convert_float(self, key, value):
        return [(self.translate(key), float(value))]

    def convert_int(self, key, value):
        return [(self.translate(key), int(value))]

    def convert_range(self, key, value):
        k = self.translate(key)
        v = float(value)
        return [(f"{k}/min", v), (f"{k}/max", v)]

    def convert_string(self, key, value):
        if isinstance(value, str):
            value = self.translate(value, key)
        return [(self.translate(key), value)]

    def convert_token(self, key, value):
        return [(self.translate(key), tokenize(value))]

    def convert_item(self, key, value):
        dispatchers = {
            "Adapted to Coarse Textured Soils": self.convert_bool,
            "Adapted to Fine Textured Soils": self.convert_bool,
            "Adapted to Medium Textured Soils": self.convert_bool,
            "Berry/Nut/Seed Product": self.convert_bool,
            "Christmas Tree Product": self.convert_ignore,
            "Cold Stratification Required": self.convert_bool,
            "Coppice Potential": self.convert_bool,
            "Fall Conspicuous": self.convert_bool,
            "Fire Resistant": self.convert_bool,
            "Flower Conspicuous": self.convert_bool,
            "Fodder Product": self.convert_bool,
            "Frost Free Days, Minimum": self.convert_int,
            "Fruit/Seed Conspicuous": self.convert_bool,
            "Fruit/Seed Persistence": self.convert_bool,
            "HasCharacteristics": self.convert_ignore,
            "HasDistributionData": self.convert_ignore,
            "HasDocumentation": self.convert_ignore,
            "HasEthnobotany": self.convert_ignore,
            "HasImages": self.convert_ignore,
            "HasInvasiveStatuses": self.convert_ignore,
            "HasLegalStatuses": self.convert_ignore,
            "HasNoxiousStatuses": self.convert_ignore,
            "HasPollinator": self.convert_ignore,
            "HasRelatedLinks": self.convert_ignore,
            "HasSubordinateTaxa": self.convert_ignore,
            "HasSynonyms": self.convert_ignore,
            "HasWetlandData": self.convert_ignore,
            "HasWildlife": self.convert_ignore,
            "Height at 20 Years, Maximum (feet)": self.convert_ignore,
            "Height, Mature (feet)": self.convert_range,
            "Known Allelopath": self.convert_bool,
            "Leaf Retention": self.convert_bool,
            "Low Growing Grass": self.convert_bool,
            "Lumber Product": self.convert_bool,
            "Naval Store Product": self.convert_bool,
            "Nursery Stock Product": self.convert_bool,
            "Palatable Human": self.convert_bool,
            "Planting Density per Acre, Maximum": self.convert_int,
            "Planting Density per Acre, Minimum": self.convert_int,
            "Post Product": self.convert_bool,
            "Precipitation, Maximum": self.convert_int,
            "Precipitation, Minimum": self.convert_int,
            "Propagated by Bare Root": self.convert_bool,
            "Propagated by Bulb": self.convert_bool,
            "Propagated by Container": self.convert_bool,
            "Propagated by Corm": self.convert_bool,
            "Propagated by Cuttings": self.convert_bool,
            "Propagated by Seed": self.convert_bool,
            "Propagated by Sod": self.convert_bool,
            "Propagated by Sprigs": self.convert_bool,
            "Propagated by Tubers": self.convert_bool,
            "Pulpwood Product": self.convert_bool,
            "Resprout Ability": self.convert_bool,
            "Root Depth, Minimum (inches)": self.convert_int,
            "ScientificName": self.convert_token,
            "Seed per Pound": self.convert_int,
            "Small Grain": self.convert_bool,
            "Temperature, Minimum (°F)": self.convert_int,
            "Veneer Product": self.convert_bool,
            "pH, Maximum": self.convert_float,
            "pH, Minimum": self.convert_float,
        }
        return dispatchers.get(key, self.convert_string)(key, value)

    def convert(self, data):
        return dict(
            chain.from_iterable(
                self.convert_item(k, v) for k, v in data.items()
            )
        )


@define(frozen=True)
class USDAModel:
    """USDA model."""

    web: USDAWeb
    storage: Storage
    converter: USDAConverter = field(factory=USDAConverter)

    @classmethod
    def from_url(cls, url: URL, cache_dir=None):
        """Instantiate USDA Plants from URL."""
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        session = HTTPSession(url).with_cache(cache_dir)
        web = USDAWeb(session)
        return cls(web, storage)

    def plant_characteristics(self, plant):
        """Return the characteristics for a single plant."""
        return self.converter.convert(
            dict(
                chain(
                    plant.items(),
                    (
                        (
                            c["PlantCharacteristicName"],
                            c["PlantCharacteristicValue"],
                        )
                        for c in self.web.plant_characteristics(plant["Id"])
                    ),
                )
            )
        )

    def all_characteristics(self):
        """Return the characteristics for all plants."""
        key = "usda-plants-all-characteristics"
        if key not in self.storage:
            search = self.web.characteristics_search()
            with ThreadPoolExecutor() as executor:
                self.storage[key] = list(
                    executor.map(
                        self.plant_characteristics,
                        search["PlantResults"],
                    )
                )

        return self.storage[key]


@define(frozen=True)
class USDADatabase(DatabaseIterablePlugin):
    model: USDAModel

    @classmethod
    def from_config(cls, config):
        model = USDAModel.from_url(
            "https://plantsservices.sc.egov.usda.gov",
            config.cache_dir,
        )
        return cls(model)

    def iterate(self):
        for c in self.model.all_characteristics():
            yield DatabaseElement(
                "USDA",
                c["scientific name"],
                [c["common name"]],
                c,
            )
