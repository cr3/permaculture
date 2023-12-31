"""Unit tests for the storage module."""

from argparse import ArgumentParser
from pathlib import Path

import pytest
from hamcrest import assert_that, has_properties, is_

from permaculture.storage import (
    FileStorage,
    MemoryStorage,
    SqliteStorage,
    StorageAction,
    null_storage,
)


@pytest.fixture(
    params=[
        "file",
        "memory",
        "sqlite",
    ]
)
def real_storage(request, tmpdir):
    """Produce pytest parameters for all storages."""
    if request.param == "file":
        yield FileStorage(tmpdir)
    elif request.param == "memory":
        yield MemoryStorage()
    elif request.param == "sqlite":
        yield SqliteStorage.from_path(tmpdir / "storage.sqlite")
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


def test_storage_action_default():
    """A SerializerAction should default to memory."""
    parser = ArgumentParser()
    parser.add_argument("--storage", action=StorageAction)
    result = parser.parse_args([])

    assert_that(
        result,
        has_properties(storage=is_(MemoryStorage)),
    )


def test_storage_action_custom():
    """A StorageAction should use the path given as argument."""
    parser = ArgumentParser()
    parser.add_argument("--storage", action=StorageAction)
    result = parser.parse_args(["--storage", "/path"])

    assert_that(
        result,
        has_properties(storage=has_properties(base_dir=Path("/path"))),
    )


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
    null_storage[key] = True
    assert not null_storage.get(key, False)


def test_null_storage_setitem(key):
    """Getting an existing key should always return the default."""
    null_storage[key] = True
    assert not null_storage.get(key, False)


def test_null_storage_delitem(key):
    """Deleting a key should always raise."""
    null_storage[key] = True
    with pytest.raises(KeyError):
        del null_storage[key]


def test_null_storage_iter(key):
    """Iterating over a null storage should return an empty list."""
    null_storage[key] = True
    assert not list(null_storage)


def test_null_storage_length(key):
    """The length of a null storage should always be 0."""
    null_storage[key] = True
    assert len(null_storage) == 0


def test_file_storage_setitem(key, tmpdir):
    """Setting a key should create the parent directory."""
    parent = tmpdir / "parent"
    assert not parent.exists()

    storage = FileStorage(parent)
    storage[key] = True
    assert parent.exists()


def test_sqlite_storage_from_path_twice(key, tmpdir):
    """Instantiating an SQLite storage from path twice should not fail."""
    path = tmpdir / "storage.sqlite"
    SqliteStorage.from_path(path)
    SqliteStorage.from_path(path)
