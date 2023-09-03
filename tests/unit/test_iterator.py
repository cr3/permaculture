"""Unit tests for the iterator module."""


from permaculture.iterator import Iterator


def test_iterator_iterate():
    """Iterating should iterate over all iterators in the registry."""
    iterator = Iterator(
        None,
        iterators={
            "a": lambda _: [1],
            "b": lambda _: [2],
        },
    )
    result = list(iterator.iterate())
    assert result == [1, 2]
