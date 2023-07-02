"""Unit test for the usda_food module."""

from unittest.mock import Mock, patch

import pytest

from permaculture.usda_food import (
    UsdaFood,
    UsdaFoodSortBy,
    UsdaFoodSortOrder,
    main,
)

from .stubs import StubRequestsResponse


def test_list():
    """List should POST with the given parameters."""
    client = Mock(post=Mock(return_value=StubRequestsResponse()))
    UsdaFood(client).list(10, 2, UsdaFoodSortBy.fdc_id, UsdaFoodSortOrder.desc)
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
