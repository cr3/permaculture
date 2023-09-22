"""Unit tests for the data module."""

import pytest

from permaculture.data import (
    flatten,
    merge,
    merge_numbers,
    merge_strings,
    unflatten,
    visit,
)


@pytest.mark.parametrize(
    "nested, flat",
    [
        pytest.param(
            ["a", "b"],
            {"0": "a", "1": "b"},
            id="list",
        ),
        pytest.param(
            [["a", "b"], "c"],
            {"0/0": "a", "0/1": "b", "1": "c"},
            id="list > list",
        ),
        pytest.param(
            [{"a": 1, "b": 2}],
            {"0/a": 1, "0/b": 2},
            id="list > dict",
        ),
        pytest.param(
            {"a": 1},
            {"a": 1},
            id="dict",
        ),
        pytest.param(
            {"a": {"b": 1}},
            {"a/b": 1},
            id="dict > dict",
        ),
        pytest.param(
            {"a": ["b"]},
            {"a/0": "b"},
            id="dict > list",
        ),
        pytest.param(
            {"a": [{"b": 1}]},
            {"a/0/b": 1},
            id="dict > list > dict",
        ),
    ],
)
def test_flatten_unflatten(nested, flat):
    """Flattening and unflattening should be reversible."""
    assert unflatten(flatten(nested)) == nested
    assert flatten(unflatten(flat)) == flat


@pytest.mark.parametrize(
    "x, y, merged",
    [
        pytest.param(
            {"a": 1},
            {"a": 1},
            {"a": 1},
            id="same key, same value",
        ),
        pytest.param(
            {"a": 1},
            {"b": 1},
            {"a": 1, "b": 1},
            id="different key, same value",
        ),
        pytest.param(
            {"a": 1},
            {"a": 2},
            {"a": [1, 2]},
            id="same key, different value",
        ),
        pytest.param(
            {"a": 1},
            {"b": 2},
            {"a": 1, "b": 2},
            id="different key, different value",
        ),
        pytest.param(
            {"a": {"b": 1}},
            {"a": {"b": 1}},
            {"a": {"b": 1}},
            id="same key, same dict value",
        ),
        pytest.param(
            {"a": {"b": 1}},
            {"a": {"b": 2}},
            {"a": {"b": [1, 2]}},
            id="same key, different dict value",
        ),
        pytest.param(
            {"a": [1]},
            {"a": [1]},
            {"a": [1]},
            id="same key, same list value",
        ),
        pytest.param(
            {"a": [1]},
            {"a": [2]},
            {"a": [1, 2]},
            id="same key, different list value",
        ),
        pytest.param(
            {"a": ""},
            {"a": "b"},
            {"a": "b"},
            id="empty x value",
        ),
        pytest.param(
            {"a": "b"},
            {"a": ""},
            {"a": "b"},
            id="empty y value",
        ),
    ],
)
def test_merge(x, y, merged):
    """Merging data should return a merged copy of the data."""
    result = merge(x, y)
    assert result == merged


@pytest.mark.parametrize(
    "x, y",
    [
        pytest.param(
            {"a": 1},
            {"a": "b"},
            id="int str",
        ),
        pytest.param(
            {"a": 1},
            {"a": []},
            id="int list",
        ),
        pytest.param(
            {"a": "b"},
            {"a": []},
            id="str list",
        ),
    ],
)
def _test_merge_error(x, y):
    """Merging data of different types should raise."""
    with pytest.raises(ValueError):
        merge(x, y)


@pytest.mark.parametrize(
    "data, f, visited",
    [
        pytest.param(
            {"a": 1},
            lambda k, v, d: v + 1,
            {"a": 2},
            id="dict",
        ),
        pytest.param(
            {"a": [1, 2, 3]},
            lambda k, v, d: sum(v),
            {"a": 6},
            id="dict > list",
        ),
        pytest.param(
            {"a": {"b": 1}},
            lambda k, v, d: v + 1 if isinstance(v, int) else v,
            {"a": {"b": 2}},
            id="dict > dict",
        ),
    ],
)
def test_visit(data, f, visited):
    """Visiting nested data should return the visited data."""
    result = visit(data, f)
    assert result == visited


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param(
            {"a": ["b"]},
            {"a": ["b"]},
            id="str",
        ),
        pytest.param(
            {"a": [1, 2, 3]},
            {"a": 2},
            id="ints",
        ),
    ],
)
def test_merge_numbers(data, expected):
    """Merging numbers should return their mean."""
    result = merge_numbers(data)
    assert result == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        pytest.param(
            {"a": [1]},
            {"a": [1]},
            id="int",
        ),
        pytest.param(
            {"a": ["b"]},
            {"a": {"b": True}},
            id="str",
        ),
    ],
)
def test_merge_strings(data, expected):
    """Merging strings should return a dictionary of booleans."""
    result = merge_strings(data)
    assert result == expected
