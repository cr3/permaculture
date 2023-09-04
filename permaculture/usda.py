"""USDA Plants API."""

from attrs import define
from yarl import URL

from permaculture.http import HTTPClient
from permaculture.iterator import IteratorElement
from permaculture.storage import FileStorage, MemoryStorage


@define(frozen=True)
class UsdaPlants:
    """USDA Plants API."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url: URL, cache_dir=None):
        """Instantiate USDA Plants from URL."""
        client = HTTPClient.with_cache_all(url, cache_dir)
        return cls(client)

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


def all_characteristics(plants, cache_dir=None):
    storage = FileStorage(cache_dir) if cache_dir else MemoryStorage()
    key = "usda-plants-all-characteristics"
    if key not in storage:
        search = plants.characteristics_search()
        storage[key] = [
            {
                **{f"General/{k}": v for k, v in r.items()},
                **{
                    "/".join(
                        [
                            c["PlantCharacteristicCategory"],
                            c["PlantCharacteristicName"],
                        ]
                    ): c["PlantCharacteristicValue"]
                    for c in plants.plant_characteristics(r["Id"])
                },
            }
            for r in search["PlantResults"]
        ]

    return storage[key]


def iterator(cache_dir):
    plants = UsdaPlants.from_url(
        "https://plantsservices.sc.egov.usda.gov",
        cache_dir,
    )
    return [
        IteratorElement(
            c["General/ScientificName"],
            [c["General/CommonName"]],
            c,
        )
        for c in all_characteristics(plants, cache_dir)
    ]
