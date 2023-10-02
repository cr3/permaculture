"""Unit functions."""

from attrs import define, field


@define(frozen=True)
class Unit:
    multiplier: float = field
    offset: float = field(default=0.0)

    def __rmul__(self, other):
        return (other + self.offset) * self.multiplier


# Distance.
foot = feet = Unit(0.3048)
inch = inches = Unit(0.0254)
km = kilometer = kilometers = Unit(1000.0)
meter = meters = Unit(1.0)
mile = miles = Unit(1609.34)

# Temperature.
celsius = Unit(1.0)
fahrenheit = Unit(5 / 9, -32)
