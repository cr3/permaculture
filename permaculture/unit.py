"""Unit functions."""

from attrs import define


@define(frozen=True)
class Unit:
    multiplier: float

    def __rmul__(self, other):
        return other * self.multiplier


feet = Unit(0.3048)
inches = Unit(0.0254)
meters = Unit(1.0)
