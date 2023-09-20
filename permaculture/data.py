"""Data manipulation functions."""

from collections.abc import Mapping
from functools import partial
from statistics import mean


def flatten(data, sep="/"):
    """Flatten nested data into flat data."""

    def _flatten(d, parent=None):
        for key, value in d:
            new_parent = f"{key}" if parent is None else f"{parent}{sep}{key}"
            if isinstance(value, Mapping):
                yield from _flatten(value.items(), new_parent)
            elif isinstance(value, list):
                yield from _flatten(enumerate(value), new_parent)
            else:
                yield new_parent, value

    d = data.items() if isinstance(data, Mapping) else enumerate(data)
    return dict(_flatten(d))


def unflatten(data, sep="/"):
    """Unflatten flat data into nested data."""
    d = None
    for key, value in data.items():
        tokens = key.split(sep)
        if d is None:
            s = d = [] if tokens[0].isdigit() else {}
        else:
            s = d

        indexed_tokens = zip(tokens, tokens[1:] + [value], strict=True)
        for count, (index, next_token) in enumerate(indexed_tokens, 1):
            if count == len(tokens):
                value = next_token
            elif next_token.isdigit():
                value = []
            else:
                value = {}

            if isinstance(s, list):
                index = int(index)
                while index >= len(s):
                    s.append(value)
            elif index not in s:
                s[index] = value

            s = s[index]

    return d


def merge(x, y):
    """Merge the data of one dict into another dict.

    If both dicts have different values for the same key, they are merged
    into a list.
    """
    d = x.copy()
    for key, y_value in y.items():
        if x_value := d.get(key):
            if isinstance(x_value, Mapping):
                d[key] = merge(x_value, y_value)
            elif isinstance(x_value, list):
                y_value = y_value if isinstance(y_value, list) else [y_value]
                d[key] = list(set(x_value + y_value))
            elif x_value != y_value:
                d[key] = (
                    x_value
                    if y_value == "" or y_value is None
                    else (
                        y_value
                        if x_value == "" or y_value is None
                        else [x_value, y_value]
                    )
                )
        else:
            d[key] = y_value

    return d


def visit(data, f):
    """Visit each key/value within nested data with the given function."""

    def _visit(d):
        for key, value in d:
            if isinstance(value, Mapping):
                yield from _visit(value.items())
            else:
                yield key, f(key, value, d)

    return dict(_visit(data.items()))


merge_strings = partial(
    visit,
    f=lambda _k, v, _d: (
        {k: True for k in v}
        if isinstance(v, list) and all(isinstance(k, str) for k in v)
        else v
    ),
)
"""Merge lists of strings into a dictionary of booleans."""


merge_numbers = partial(
    visit,
    f=lambda _k, v, _d: (
        mean(v)
        if isinstance(v, list) and all(isinstance(k, int | float) for k in v)
        else v
    ),
)
"""Merge lists of floats into their mean."""
