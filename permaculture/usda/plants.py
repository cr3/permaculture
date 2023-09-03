"""USDA Plants API."""

from attrs import define

from permaculture.http import HTTPClient
from permaculture.iterator import IteratorElement


@define(frozen=True)
class UsdaPlants:
    """USDA Plants API."""

    client: HTTPClient

    @classmethod
    def from_url(cls, url, cache_dir=None):
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
        response = self.client.post("CharacteristicsSearch", json=payload)
        return response.json()

    def plant_profile(self, symbol):
        """Plant profile for a symbol."""
        response = self.client.get("PlantProfile", params={"symbol": symbol})
        return response.json()

    def plant_characteristics(self, Id):
        """Plant characteristics for an identifier."""
        response = self.client.get(f"PlantCharacteristics/{Id}")
        return response.json()


def all_characteristics(plants):
    search = plants.characteristics_search()
    return [
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


def iterator(cache_dir=None):
    plants = UsdaPlants.from_url(
        "https://plantsservices.sc.egov.usda.gov/api",
        cache_dir,
    )
    return [
        IteratorElement(
            c["General/ScientificName"],
            list(filter(None, [c["General/CommonName"]])),
            c,
        )
        for c in all_characteristics(plants)
    ]
