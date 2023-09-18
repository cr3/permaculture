"""Unit tests for the unit module."""

import math

import pytest

from permaculture.unit import (
    feet,
    inches,
    meters,
)


@pytest.mark.parametrize(
    "a, b",
    [
        pytest.param(1 * feet, 0.3048 * meters, id="feet to meters"),
        pytest.param(1 * meters, 3.28084 * feet, id="meters to feet"),
        pytest.param(1 * feet, 12 * inches, id="feet to inches"),
    ],
)
def test_length_unit(a, b):
    """It should be convenient to convert between units."""
    assert math.isclose(a, b, rel_tol=1e-6, abs_tol=0.0)
