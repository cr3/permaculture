"""Unit tests for the storage module."""


from argparse import ArgumentParser

import pytest
from yarl import URL

from permaculture.storage import (
    FileStorage,
    MemoryStorage,
    SqliteStorage,
    StorageAction,
    null_storage,
)


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
    """A StorageAction with no args should use the default."""
    parser = ArgumentParser()
    parser.add_argument("--storage", action=StorageAction)
    result = parser.parse_args([])

    assert result.storage is None


def test_storage_action_default_path(tmp_path):
    """A StorageAction with a default path should produce a FileStorage."""
    parser = ArgumentParser()
    parser.add_argument("--storage", action=StorageAction, default=str(tmp_path))
    result = parser.parse_args([])

    assert isinstance(result.storage, FileStorage)


def test_storage_action_custom(tmp_path):
    """A StorageAction should use the URL given as argument."""
    parser = ArgumentParser()
    parser.add_argument("--storage", action=StorageAction)
    result = parser.parse_args(["--storage", str(tmp_path)])

    assert isinstance(result.storage, FileStorage)


def test_storage_action_memory():
    """A StorageAction with memory:// should produce a MemoryStorage."""
    parser = ArgumentParser()
    parser.add_argument("--storage", action=StorageAction)
    result = parser.parse_args(["--storage", "memory://"])

    assert isinstance(result.storage, MemoryStorage)


def test_storage_getitem_non_existing(key, storage):
    """Getting a non-existing key should return the default value."""
    assert storage.get(key, True)


def test_storage_getitem_existing(key, storage):
    """Getting a stored key should only return its value."""
    storage[key] = True
    assert storage.get(key, False)


def test_storage_delitem_non_existing(key, storage):
    """Deleting a non-existing key should raise a KeyError."""
    with pytest.raises(KeyError):
        del storage[key]


def test_storage_delitem_existing(key, storage):
    """Deleting a stored key should then return the default value."""
    storage[key] = True
    del storage[key]
    assert storage.get(key, True)


def test_storage_iter(key, storage):
    """Iterating over a storage should return the keys."""
    storage[key] = True
    assert list(storage) == [key]


def test_storage_length(key, storage):
    """The length should return the number of stored keys."""
    assert len(storage) == 0
    storage[key] = True
    assert len(storage) == 1


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


@pytest.mark.parametrize(
    "url, path",
    [
        ("file://aaa", "aaa"),
        ("file:///aaa", "/aaa"),
        ("c:a", "c:a"),
        ("c:/a", "c:/a"),
        ("c:\\a", "c:/a"),
        ("a", "a"),
        ("/a", "/a"),
        ("a/b", "a/b"),
        ("/a/b", "/a/b"),
    ],
)
def test_file_storage_from_url(url, path):
    """Test file storage from URL matches the expected key."""
    storage = FileStorage.from_url(url)
    assert storage.path.as_posix() == path


def test_file_storage_setitem(key, tmpdir):
    """Setting a key should create the parent directory."""
    parent = tmpdir / "parent"
    assert not parent.exists()

    storage = FileStorage.from_url(parent)
    storage[key] = True
    assert parent.exists()


def test_sqlite_storage_from_url_twice(key, tmpdir):
    """Instantiating an SQLite storage from file twice should not fail."""
    path = tmpdir / "test.db"
    url = URL.build(scheme="sqlite", path=str(path))
    SqliteStorage.from_url(url)
    SqliteStorage.from_url(url)
