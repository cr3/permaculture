"""Unit test for the fdc module."""

from unittest.mock import Mock, patch

import pytest

from permaculture.usda.fdc import (
    UsdaFdc,
    UsdaFdcSortBy,
    UsdaFdcSortOrder,
    main,
)

from ..stubs import StubRequestsResponse


def test_food():
    """Food should GET with the given fdc identifier."""
    client = Mock(get=Mock(return_value=StubRequestsResponse()))
    UsdaFdc(client).food(10)
    client.get.assert_called_once_with("v1/food/10", params={"format": "full"})


def test_foods():
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


def test_foods_list():
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


@patch("sys.stdout")
def test_main_help(stdout):
    """The main function should output usage when asked for --help."""
    with pytest.raises(SystemExit):
        main(["--help"])

    stdout.write.call_args[0][0].startswith("usage")
