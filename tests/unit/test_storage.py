"""Unit tests for the storage module."""

import pytest

from permaculture.storage import FileStorage, MemoryStorage, NullStorage


@pytest.fixture(
    params=[
        "file",
        "memory",
    ]
)
def real_storage(request, tmpdir):
    """Produce pytest parameters for all storages."""
    if request.param == "file":
        yield FileStorage(tmpdir)
    elif request.param == "memory":
        yield MemoryStorage()
    else:
        raise KeyError(f"Unsupported storage type: {request.param}")


@pytest.fixture(
    params=[
        "a",
        "a/b",
        "http://a/b",
    ]
)
def key(request):
    """Produce a key to test the storage."""
    return request.param


def test_real_storage_getitem_non_existing(key, real_storage):
    """Getting a non-existing key should return the default value."""
    assert real_storage.get(key, True)


def test_real_storage_getitem_existing(key, real_storage):
    """Getting a stored key should only return its value."""
    real_storage[key] = True
    assert real_storage.get(key, False)


def test_real_storage_delitem_non_existing(key, real_storage):
    """Deleting a non-existing key should raise a KeyError."""
    with pytest.raises(KeyError):
        del real_storage[key]


def test_real_storage_delitem_existing(key, real_storage):
    """Deleting a stored key should then return the default value."""
    real_storage[key] = True
    del real_storage[key]
    assert real_storage.get(key, True)


def test_real_storage_iter(key, real_storage):
    """Iterating over a storage should return the keys."""
    real_storage[key] = True
    assert list(real_storage) == [key]


def test_real_storage_length(key, real_storage):
    """The length should return the number of stored keys."""
    assert len(real_storage) == 0
    real_storage[key] = True
    assert len(real_storage) == 1


def test_null_storage_getitem(key):
    """Getting an existing key should always return the default."""
    storage = NullStorage()
    storage[key] = True
    assert not storage.get(key, False)


def test_null_storage_setitem(key):
    """Getting an existing key should always return the default."""
    storage = NullStorage()
    storage[key] = True
    assert not storage.get(key, False)


def test_null_storage_iter(key):
    """Iterating over a null storage should return an empty list."""
    storage = NullStorage()
    storage[key] = True
    assert not list(storage)


def test_null_storage_length(key):
    """The length of a null storage should always be 0."""
    storage = NullStorage()
    storage[key] = True
    assert len(storage) == 0
