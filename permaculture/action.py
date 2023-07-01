"""Action utilities."""

from argparse import Action


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
