"""Unit tests for the unit module."""

import math

import pytest

from permaculture.unit import (
    celsius,
    fahrenheit,
    feet,
    inches,
    km,
    meters,
    miles,
)


@pytest.mark.parametrize(
    "a, b",
    [
        pytest.param(1 * feet, 0.3048 * meters, id="feet to meters"),
        pytest.param(1 * meters, 3.28084 * feet, id="meters to feet"),
        pytest.param(1 * feet, 12 * inches, id="feet to inches"),
        pytest.param(
            100 * celsius, 212 * fahrenheit, id="celsius to fahrenheit"
        ),
        pytest.param(1 * km, 1000 * meters, id="km to meters"),
        pytest.param(1 * km, 0.621371 * miles, id="km to miles"),
    ],
)
def test_unit_rmul(a, b):
    """It should be convenient to convert between units."""
    assert math.isclose(a, b, rel_tol=1e-5, abs_tol=0.0)
