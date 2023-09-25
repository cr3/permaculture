"""Unit functions."""

from attrs import define, field


@define(frozen=True)
class Unit:
    multiplier: float = field
    offset: float = field(default=0.0)

    def __rmul__(self, other):
        return (other + self.offset) * self.multiplier


feet = Unit(0.3048)
inches = Unit(0.0254)
meters = Unit(1.0)

celsius = Unit(1.0)
fahrenheit = Unit(5 / 9, -32)
