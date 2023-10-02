"""Data manipulation functions.

Flattening nested data into flat data:

    >>> flatten({'a': {'b': 1}})
    {'a/b': 1}

Unflattening flat data into nested data:

    >>> unflatten({'a/b': 1})
    {'a': {'b': 1}}

Merging a list of dictionaries by calculating the mean on collision:

    >>> merge([{'a': 1}, {'a': 2}], lambda _, v: sum(v)/len(v))
    {'a': 1.5}
"""

from collections.abc import Mapping
from itertools import groupby
from operator import itemgetter
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
            elif isinstance(s, dict):
                if index not in s:
                    s[index] = value
            else:
                raise TypeError(f"Conflicting types for {key!r} in {data}")

            s = s[index]

    return d


def resolve(key, values):
    """Default function to resolve collisions when merging dictionaries."""
    if isinstance(values[0], str):
        values = [v for v in values if v != ""]
        return values[0] if len(values) == 1 else values
    elif isinstance(values[0], float | int):
        return mean(values)
    else:
        raise TypeError(f"Unsupported values for {key!r}: {values!r}")


def merge(dicts, resolve=resolve):
    """Merge a list of dictionaries by resolving collisions.

    :param resolve: Function called on collision to resolve colliding values.
    """
    d = {}

    for key, values in groupby(
        sorted((item for d in dicts for item in d.items()), key=itemgetter(0)),
        itemgetter(0),
    ):
        values = list(map(itemgetter(1), values))
        if len(set(map(type, values))) > 1:
            raise ValueError(f"Different types for {key!r}: {values!r}")

        if isinstance(values[0], Mapping):
            d[key] = merge(values, resolve)
        elif isinstance(values[0], list):
            d[key] = list({i for v in values for i in v})
        elif len(values) == 1 or len(set(values)) == 1:
            d[key] = values[0]
        else:
            d[key] = resolve(key, values)

    return d
