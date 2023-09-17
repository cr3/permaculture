"""USDA Plants database."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from itertools import chain

from attrs import define, field
from yarl import URL

from permaculture.database import DatabaseElement, DatabaseIterablePlugin
from permaculture.http import HTTPClient
from permaculture.locales import Locales
from permaculture.storage import FileStorage, MemoryStorage, Storage


@define(frozen=True)
class USDAWeb:
    """USDA web interface."""

    client: HTTPClient

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
        response = self.client.post("/api/CharacteristicsSearch", json=payload)
        return response.json()

    def plant_profile(self, symbol):
        """Plant profile for a symbol."""
        response = self.client.get(
            "/api/PlantProfile", params={"symbol": symbol}
        )
        return response.json()

    def plant_characteristics(self, Id):
        """Plant characteristics for an identifier."""
        response = self.client.get(f"/api/PlantCharacteristics/{Id}")
        return response.json()


@define(frozen=True)
class USDAModel:
    """USDA model."""

    web: USDAWeb
    storage: Storage
    locales: Locales = field(factory=partial(Locales.from_domain, "usda"))

    @classmethod
    def from_url(cls, url: URL, cache_dir=None):
        """Instantiate USDA Plants from URL."""
        storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
        client = HTTPClient(url).with_cache(cache_dir)
        web = USDAWeb(client)
        return cls(web, storage)

    def convert(self, key, value):
        def to_bool(old_value):
            if old_value == "Yes":
                return True
            elif old_value == "No":
                return False
            else:
                raise ValueError(f"Unknown boolean: {old_value}")

        def to_str(old_value):
            return self.locales.translate(old_value, key).lower()

        types = {
            "Adapted to Coarse Textured Soils": to_bool,
            "Adapted to Fine Textured Soils": to_bool,
            "Adapted to Medium Textured Soils": to_bool,
            "Berry/Nut/Seed Product": to_bool,
            "Christmas Tree Product": to_bool,
            "Cold Stratification Required": to_bool,
            "Coppice Potential": to_bool,
            "Fall Conspicuous": to_bool,
            "Fire Resistant": to_bool,
            "Flower Conspicuous": to_bool,
            "Fodder Product": to_bool,
            "Frost Free Days, Minimum": int,
            "Fruit/Seed Conspicuous": to_bool,
            "Fruit/Seed Persistence": to_bool,
            "Height at 20 Years, Maximum (feet)": int,
            "Height, Mature (feet)": float,
            "Known Allelopath": to_bool,
            "Leaf Retention": to_bool,
            "Low Growing Grass": to_bool,
            "Lumber Product": to_bool,
            "Naval Store Product": to_bool,
            "Nursery Stock Product": to_bool,
            "Palatable Human": to_bool,
            "Planting Density per Acre, Maximum": int,
            "Planting Density per Acre, Minimum": int,
            "Post Product": to_bool,
            "Precipitation, Maximum": int,
            "Precipitation, Minimum": int,
            "Propagated by Bare Root": to_bool,
            "Propagated by Bulb": to_bool,
            "Propagated by Container": to_bool,
            "Propagated by Corm": to_bool,
            "Propagated by Cuttings": to_bool,
            "Propagated by Seed": to_bool,
            "Propagated by Sod": to_bool,
            "Propagated by Sprigs": to_bool,
            "Propagated by Tubers": to_bool,
            "Pulpwood Product": to_bool,
            "Resprout Ability": to_bool,
            "Root Depth, Minimum (inches)": int,
            "Seed per Pound": int,
            "Small Grain": to_bool,
            "Temperature, Minimum (°F)": int,
            "Veneer Product": to_bool,
            "pH, Maximum": float,
            "pH, Minimum": float,
        }
        if isinstance(value, str):
            value = types.get(key, to_str)(value)
        return to_str(key), value

    def plant_characteristics(self, plant):
        """Return the characteristics for a single plant."""
        return dict(
            self.convert(k, v)
            for k, v in chain(
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
