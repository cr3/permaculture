"""Action utilities."""

from argparse import Action


def enum_action(enum):
    """Return an argparse action class for an Enum type."""

    class EnumAction(Action):
        """Argparse action for an Enum type."""

        def __init__(self, option_strings, dest, **kwargs):
            """Initialize enum defaults."""
            kwargs.setdefault("choices", [t.name for t in enum])
            super().__init__(option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            """Set the dest attribute to the Enum type."""
            if isinstance(values, list):
                values = [enum[v] for v in values]
            else:
                values = enum[values]

            setattr(namespace, self.dest, values)

    return EnumAction


class SingleAction(Action):
    """Argparse action where nargs is not allowed."""

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        """Raise a ValueError if nargs is set."""
        if nargs is not None:
            raise ValueError("nargs not allowed")

        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Set the dest attribute in the namespace."""
        setattr(namespace, self.dest, values)
