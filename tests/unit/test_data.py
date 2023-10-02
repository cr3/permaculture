"""Unit tests for the data module."""

import pytest

from permaculture.data import (
    flatten,
    merge,
    unflatten,
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


def test_unflatten_error():
    """Unflattening conflicting types should raise."""
    with pytest.raises(TypeError):
        unflatten({"a": "", "a/b": True})


@pytest.mark.parametrize(
    "dicts, merged",
    [
        pytest.param(
            [{"a": 1}, {"a": 1}],
            {"a": 1},
            id="same key, same value",
        ),
        pytest.param(
            [{"a": 1}, {"b": 1}],
            {"a": 1, "b": 1},
            id="different key, same value",
        ),
        pytest.param(
            [{"a": 1}, {"a": 2}],
            {"a": 1.5},
            id="same key, different value",
        ),
        pytest.param(
            [{"a": 1}, {"b": 2}],
            {"a": 1, "b": 2},
            id="different key, different value",
        ),
        pytest.param(
            [{"a": {"b": 1}}, {"a": {"b": 1}}],
            {"a": {"b": 1}},
            id="same key, same dict value",
        ),
        pytest.param(
            [{"a": {"b": 1}}, {"a": {"b": 2}}],
            {"a": {"b": 1.5}},
            id="same key, different dict value",
        ),
        pytest.param(
            [{"a": [1]}, {"a": [1]}],
            {"a": [1]},
            id="same key, same list value",
        ),
        pytest.param(
            [{"a": [1]}, {"a": [2]}],
            {"a": [1, 2]},
            id="same key, different list value",
        ),
        pytest.param(
            [{"a": "b"}, {"a": ""}],
            {"a": "b"},
            id="empty string value",
        ),
    ],
)
def test_merge(dicts, merged):
    """Merging dictionaries should return a merged dictionary."""
    result = merge(dicts)
    assert result == merged


@pytest.mark.parametrize(
    "dicts",
    [
        pytest.param(
            [{"a": 1}, {"a": "b"}],
            id="int str",
        ),
        pytest.param(
            [{"a": 1}, {"a": []}],
            id="int list",
        ),
        pytest.param(
            [{"a": "b"}, {"a": []}],
            id="str list",
        ),
    ],
)
def test_merge_error(dicts):
    """Merging data of different types should raise."""
    with pytest.raises(ValueError):
        merge(dicts)
