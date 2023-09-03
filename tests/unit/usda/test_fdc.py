"""Unit tests for the USDA fdc module."""

from unittest.mock import Mock

from permaculture.usda.fdc import (
    UsdaFdc,
    UsdaFdcSortBy,
    UsdaFdcSortOrder,
)

from ..stubs import StubRequestsResponse


def test_usda_fdc_food():
    """Food should GET with the given fdc identifier."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    UsdaFdc(client).food(10)
    client.get.assert_called_once_with("v1/food/10", params={"format": "full"})


def test_usda_fdc_foods():
    """Foods should POST with the given fdc identifiers."""
    client = Mock(post=Mock(return_value=StubRequestsResponse()))
    UsdaFdc(client).foods([1, 2, 3])
    client.post.assert_called_once_with(
        "v1/foods",
        json={
            "fdcIds": [1, 2, 3],
            "format": "full",
        },
    )


def test_usd_fdc_foods_list():
    """Foods list should POST with the given parameters."""
    client = Mock(post=Mock(return_value=StubRequestsResponse()))
    UsdaFdc(client).foods_list(
        10,
        2,
        UsdaFdcSortBy.fdc_id,
        UsdaFdcSortOrder.desc,
    )
    client.post.assert_called_once_with(
        "v1/foods/list",
        json={
            "pageSize": 10,
            "pageNumber": 2,
            "sort_by": "fdcId",
            "sort_order": "desc",
        },
    )
