"""Unit tests for the cache module."""

import pytest

from permaculture.cache import FileCache, MemoryCache, NullCache


@pytest.fixture(
    params=[
        "file",
        "memory",
    ]
)
def real_cache(request, tmpdir):
    """Produce pytest parameters for all caches."""
    if request.param == "file":
        yield FileCache(tmpdir)
    elif request.param == "memory":
        yield MemoryCache()
    else:
        raise KeyError(f"Unsupported cache type: {request.param}")


@pytest.fixture(
    params=[
        "a",
        "a/b",
        "http://a/b",
    ]
)
def key(request):
    """Produce a key to test the cache."""
    return request.param


def test_real_cache_retrieve_non_existing(key, real_cache):
    """Retrieving a non-existing key should return the default value."""
    assert real_cache.retrieve(key, True)


def test_real_cache_retrieve_existing(key, real_cache):
    """Retrieving a stored key should only return its value."""
    real_cache.store(key, True)
    assert real_cache.retrieve(key, False)


def test_real_cache_discard_non_existing(key, real_cache):
    """Discarding a non-existing key should do nothing."""
    real_cache.discard(key)


def test_real_cache_discard_existing(key, real_cache):
    """Discarding a stored key should then return the default value."""
    real_cache.store(key, True)
    real_cache.discard(key)
    assert real_cache.retrieve(key, True)


def test_real_cache_length(real_cache):
    """The length should return the number of stored keys."""
    assert len(real_cache) == 0
    real_cache.store("test", True)
    assert len(real_cache) == 1


def test_null_cache_retrieve(key):
    """Retrieving an existing key should always return the default."""
    null_cache = NullCache()
    null_cache.store(key, True)
    assert not null_cache.retrieve(key, False)


def test_null_cache_length():
    """The length of a null cache should always be 0."""
    null_cache = NullCache()
    null_cache.store("test", True)
    assert len(null_cache) == 0
