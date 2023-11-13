"""USDA Plants database."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial

from attrs import define, field
from requests.exceptions import HTTPError

from permaculture.converter import Converter
from permaculture.database import Database, DatabasePlant
from permaculture.http import HTTPSession
from permaculture.locales import Locales
from permaculture.nlp import normalize
from permaculture.priority import LocationPriority, Priority
from permaculture.unit import fahrenheit, feet, inches

PLANTS_ORIGIN = "https://plantsservices.sc.egov.usda.gov"


@define(frozen=True)
class PlantsWeb:
    """USDA Plants web interface."""

    session: HTTPSession = field(factory=partial(HTTPSession, PLANTS_ORIGIN))

    def characteristics_search(self, **kwargs):
        """Search characteristics."""
        payload = {
            "ArtistFirstLetters": None,
            "Artists": None,
            "Cities": None,
            "CopyrightStatuses": None,
            "Counties": None,
            "Countries": None,
            "Durations": None,
            "Field": None,
            "FilterOptions": None,
            "Groups": None,
            "GrowthHabits": None,
            "ImageLocations": None,
            "ImageTypes": None,
            "InvasiveLocations": None,
            "Localities": None,
            "Locations": None,
            "MasterId": -1,
            "NoxiousLocations": None,
            "Offset": None,
            "Provinces": None,
            "SortBy": "sortSciName",
            "TaxonSearchCriteria": None,
            "Text": None,
            "Type": "Characteristics",
            "UnfilteredPlantIds": None,
            "WetlandRegions": None,
            **kwargs,
        }
        response = self.session.post(
            "/api/CharacteristicsSearch",
            json=payload,
        )
        return response.json()

    def plant_search(self, **kwargs):
        """Search plants."""
        payload = {
            "ArtistFirstLetters": None,
            "Artists": None,
            "Cities": None,
            "CopyrightStatuses": None,
            "Counties": None,
            "Countries": None,
            "Durations": None,
            "Field": None,
            "FilterOptions": None,
            "Groups": None,
            "GrowthHabits": None,
            "ImageLocations": None,
            "ImageTypes": None,
            "InvasiveLocations": None,
            "Localities": None,
            "Locations": None,
            "MasterId": -1,
            "NoxiousLocations": None,
            "Offset": -1,
            "Provinces": None,
            "SortBy": None,
            "TaxonSearchCriteria": None,
            "Text": None,
            "Type": "Characteristics",
            "UnfilteredPlantIds": None,
            "WetlandRegions": None,
            **kwargs,
        }
        response = self.session.post(
            "/api/PlantSearch",
            json=payload,
        )
        return response.json()

    def plant_profile(self, symbol):
        """Plant profile for a symbol."""
        response = self.session.get(
            "/api/PlantProfile",
            params={"symbol": symbol},
        )
        return response.json()

    def plant_characteristics(self, Id):
        """Plant characteristics for an identifier."""
        response = self.session.get(f"/api/PlantCharacteristics/{Id}")
        return response.json()


@define(frozen=True)
class PlantsConverter(Converter):
    locales: Locales = field(
        factory=partial(Locales.from_domain, "usda-plants")
    )

    def convert_item(self, key, value):
        dispatchers = {
            "AcceptedId": self.convert_ignore,
            "Adapted to Coarse Textured Soils": self.convert_bool,
            "Adapted to Fine Textured Soils": self.convert_bool,
            "Adapted to Medium Textured Soils": self.convert_bool,
            "Berry/Nut/Seed Product": self.convert_bool,
            "Christmas Tree Product": self.convert_ignore,
            "Cold Stratification Required": self.convert_bool,
            "CommonName": self.convert_list,
            "Coppice Potential": self.convert_bool,
            "Fall Conspicuous": self.convert_bool,
            "Fire Resistant": self.convert_bool,
            "Flower Conspicuous": self.convert_bool,
            "Flower Color": self.convert_list,
            "Fodder Product": self.convert_bool,
            "Foliage Color": self.convert_list,
            "Frost Free Days, Minimum": self.convert_int,
            "Fruit/Seed Conspicuous": self.convert_bool,
            "Fruit/Seed Persistence": self.convert_bool,
            "Growth Rate": self.convert_list,
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
            "Height, Mature (feet)": partial(self.convert_float, unit=feet),
            "Id": self.convert_ignore,
            "ImageId": self.convert_ignore,
            "Known Allelopath": self.convert_bool,
            "Leaf Retention": self.convert_bool,
            "Low Growing Grass": self.convert_bool,
            "Lumber Product": self.convert_bool,
            "Naval Store Product": self.convert_bool,
            "Nursery Stock Product": self.convert_bool,
            "Palatable Human": self.convert_bool,
            "PlantLocationId": self.convert_ignore,
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
            "RankId": self.convert_ignore,
            "Resprout Ability": self.convert_bool,
            "Root Depth, Minimum (inches)": partial(
                self.convert_float, unit=inches
            ),
            "ScientificName": self.convert_token,
            "Seed per Pound": self.convert_int,
            "Small Grain": self.convert_bool,
            "Symbol": self.convert_ignore,
            "Synonyms": self.convert_ignore,
            "Temperature, Minimum (°F)": partial(
                self.convert_float, unit=fahrenheit
            ),
            "Veneer Product": self.convert_bool,
            "pH, Maximum": self.convert_float,
            "pH, Minimum": self.convert_float,
        }
        return dispatchers.get(key, self.convert_string)(key, value)


@define(frozen=True)
class PlantsModel:
    """USDA Plants model."""

    web: PlantsWeb = field(factory=PlantsWeb)
    converter: PlantsConverter = field(factory=PlantsConverter)

    def with_cache(self, storage):
        self.web.session.with_cache(storage)
        return self

    def plant_characteristics(self, plant):
        """Return the characteristics for a single plant."""
        return self.converter.convert(
            {
                **plant,
                **{
                    c["PlantCharacteristicName"]: c["PlantCharacteristicValue"]
                    for c in self.web.plant_characteristics(plant["Id"])
                },
            }
        )

    def plant_search(self, text, field):
        try:
            search = self.web.plant_search(
                Field=field,
                SortBy="sortSciName",
                Text=text,
            )
        except HTTPError:
            return []

        for plant in search["PlantResults"]:
            yield self.plant_characteristics(plant)

    def all_characteristics(self):
        """Return the characteristics for all plants."""
        search = self.web.characteristics_search()
        with ThreadPoolExecutor() as executor:
            return executor.map(
                self.plant_characteristics,
                search["PlantResults"],
            )


@define(frozen=True)
class PlantsDatabase(Database):
    model: PlantsModel = field(factory=PlantsModel)
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config):
        """Instantiate PlantsDatabase from config."""
        model = PlantsModel().with_cache(config.storage)
        priority = LocationPriority("United States").with_cache(config.storage)
        return cls(model, priority)

    def iterate(self):
        return (
            DatabasePlant(c, self.priority.weight)
            for c in self.model.all_characteristics()
        )

    def lookup(self, names, score):
        for name in names:
            normalized_name = normalize(name)
            for plant in self.model.plant_search(
                normalized_name, "Scientific Name"
            ):
                if self.extract(plant["scientific name"], names) >= score:
                    yield DatabasePlant(plant, self.priority.weight)

    def search(self, name, score):
        normalized_name = normalize(name)
        for plant in self.model.plant_search(normalized_name, "Common Name"):
            plant = DatabasePlant(plant, self.priority.weight)
            if self.extract(name, plant.names) >= score:
                yield plant
