"""USDA Plants database."""

import logging
from functools import partial

from attrs import define, field
from requests.exceptions import HTTPError

from permaculture.converter import Converter
from permaculture.http import HTTPSession
from permaculture.locales import Locales
from permaculture.plant import IngestorPlant
from permaculture.priority import LocationPriority, Priority
from permaculture.unit import fahrenheit, feet, inches

USDA_ORIGIN = "https://plantsservices.sc.egov.usda.gov"

logger = logging.getLogger(__name__)


@define(frozen=True)
class USDAWeb:
    """USDA Plants web interface."""

    session: HTTPSession = field(
        factory=partial(HTTPSession, USDA_ORIGIN, headers={"Accept": "application/json"}),
    )

    def source_url(self):
        """Return the origin URL for this data source."""
        return self.session.origin

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
class USDAConverter(Converter):
    locales: Locales = field(
        factory=partial(Locales.from_domain, "usda")
    )

    DISPATCH = {
        "AcceptedId": Converter.convert_ignore,
        "Adapted to Coarse Textured Soils": Converter.convert_bool,
        "Adapted to Fine Textured Soils": Converter.convert_bool,
        "Adapted to Medium Textured Soils": Converter.convert_bool,
        "Berry/Nut/Seed Product": Converter.convert_bool,
        "Christmas Tree Product": Converter.convert_ignore,
        "Cold Stratification Required": Converter.convert_bool,
        "CommonName": Converter.convert_list,
        "Coppice Potential": Converter.convert_bool,
        "Fall Conspicuous": Converter.convert_bool,
        "Fire Resistant": Converter.convert_bool,
        "Flower Conspicuous": Converter.convert_bool,
        "Flower Color": Converter.convert_list,
        "Fodder Product": Converter.convert_bool,
        "Foliage Color": Converter.convert_list,
        "Frost Free Days, Minimum": Converter.convert_int,
        "Fruit/Seed Conspicuous": Converter.convert_bool,
        "Fruit/Seed Persistence": Converter.convert_bool,
        "Growth Rate": Converter.convert_list,
        "HasCharacteristics": Converter.convert_ignore,
        "HasDistributionData": Converter.convert_ignore,
        "HasDocumentation": Converter.convert_ignore,
        "HasEthnobotany": Converter.convert_ignore,
        "HasImages": Converter.convert_ignore,
        "HasInvasiveStatuses": Converter.convert_ignore,
        "HasLegalStatuses": Converter.convert_ignore,
        "HasNoxiousStatuses": Converter.convert_ignore,
        "HasPollinator": Converter.convert_ignore,
        "HasRelatedLinks": Converter.convert_ignore,
        "HasSubordinateTaxa": Converter.convert_ignore,
        "HasSynonyms": Converter.convert_ignore,
        "HasWetlandData": Converter.convert_ignore,
        "HasWildlife": Converter.convert_ignore,
        "Height at 20 Years, Maximum (feet)": Converter.convert_ignore,
        "Height, Mature (feet)": partial(Converter.convert_float, unit=feet),
        "Id": Converter.convert_ignore,
        "ImageId": Converter.convert_ignore,
        "Known Allelopath": Converter.convert_bool,
        "Leaf Retention": Converter.convert_bool,
        "Low Growing Grass": Converter.convert_bool,
        "Lumber Product": Converter.convert_bool,
        "Naval Store Product": Converter.convert_bool,
        "Nursery Stock Product": Converter.convert_bool,
        "Palatable Human": Converter.convert_bool,
        "PlantLocationId": Converter.convert_ignore,
        "Planting Density per Acre, Maximum": Converter.convert_int,
        "Planting Density per Acre, Minimum": Converter.convert_int,
        "Post Product": Converter.convert_bool,
        "Precipitation, Maximum": Converter.convert_int,
        "Precipitation, Minimum": Converter.convert_int,
        "Propagated by Bare Root": Converter.convert_bool,
        "Propagated by Bulb": Converter.convert_bool,
        "Propagated by Container": Converter.convert_bool,
        "Propagated by Corm": Converter.convert_bool,
        "Propagated by Cuttings": Converter.convert_bool,
        "Propagated by Seed": Converter.convert_bool,
        "Propagated by Sod": Converter.convert_bool,
        "Propagated by Sprigs": Converter.convert_bool,
        "Propagated by Tubers": Converter.convert_bool,
        "Pulpwood Product": Converter.convert_bool,
        "RankId": Converter.convert_ignore,
        "Resprout Ability": Converter.convert_bool,
        "Root Depth, Minimum (inches)": partial(Converter.convert_float, unit=inches),
        "ScientificName": Converter.convert_token,
        "Seed per Pound": Converter.convert_int,
        "Small Grain": Converter.convert_bool,
        "Symbol": Converter.convert_ignore,
        "Synonyms": Converter.convert_ignore,
        "Temperature, Minimum (°F)": partial(Converter.convert_float, unit=fahrenheit),
        "Veneer Product": Converter.convert_bool,
        "pH, Maximum": Converter.convert_float,
        "pH, Minimum": Converter.convert_float,
    }


@define(frozen=True)
class USDAModel:
    """USDA Plants model."""

    web: USDAWeb = field(factory=USDAWeb)
    converter: USDAConverter = field(factory=USDAConverter)

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
        for plant in search["PlantResults"]:
            yield self.plant_characteristics(plant)


@define(frozen=True)
class USDAIngestor:
    name: str
    title: str = "USDA Plants"
    model: USDAModel = field(factory=USDAModel)
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config, name):
        """Instantiate USDAIngestor from config."""
        model = USDAModel().with_cache(config.storage)
        priority = LocationPriority("United States").with_cache(config.storage)
        return cls(name, model=model, priority=priority)

    def fetch_all(self):
        count = 0
        for c in self.model.all_characteristics():
            count += 1
            if count % 100 == 0:
                logger.info("USDA: ingested %d plants", count)
            yield IngestorPlant(
                c, self.priority.weight,
                ingestor=self.name, title=self.title, source=self.model.web.source_url(),
            )
        logger.info("USDA: ingested %d plants total", count)
