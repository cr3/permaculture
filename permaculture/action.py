"""Action utilities."""

from argparse import Action


class EnumAction(Action):
    """Argparse action for an Enum type."""

    def __init__(self, option_strings, dest, type, **kwargs):  # noqa: A002
        """Initialize enum defaults."""
        self._enum = type
        kwargs.setdefault("choices", [t.name for t in type])
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Set the dest attribute to the enum type."""
        if isinstance(values, list):
            values = [self._enum[v] for v in values]
        else:
            values = self._enum[values]

        setattr(namespace, self.dest, values)


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
